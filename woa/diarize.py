import warnings
from functools import partial
from typing import Optional
import numpy as np
import pytorch_lightning as pl
import torch
import torch.nn.functional as F
import torchaudio.compliance.kaldi as kaldi
from einops import rearrange
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import cdist
from torch import nn

class StatsPool(nn.Module):
   
    def _pool(self, sequences: torch.Tensor, weights: torch.Tensor) -> torch.Tensor:
        weights = weights.unsqueeze(dim=1)

        v1 = weights.sum(dim=2) + 1e-8
        mean = torch.sum(sequences * weights, dim=2) / v1

        dx2 = torch.square(sequences - mean.unsqueeze(2))
        v2 = torch.square(weights).sum(dim=2)

        var = torch.sum(dx2 * weights, dim=2) / (v1 - v2 / v1 + 1e-8)
        std = torch.sqrt(var)

        return torch.cat([mean, std], dim=1)

    def forward(
        self, sequences: torch.Tensor, weights: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        if weights is None:
            mean = sequences.mean(dim=-1)
            std = sequences.std(dim=-1, correction=1)
            return torch.cat([mean, std], dim=-1)

        if weights.dim() == 2:
            has_speaker_dimension = False
            weights = weights.unsqueeze(dim=1)

        else:
            has_speaker_dimension = True

        _, _, num_frames = sequences.shape
        _, _, num_weights = weights.shape
        if num_frames != num_weights:
            warnings.warn(
                f"Mismatch between frames ({num_frames}) and weights ({num_weights}) numbers."
            )
            weights = F.interpolate(weights, size=num_frames, mode="nearest")

        output = rearrange(
            torch.vmap(self._pool, in_dims=(None, 1))(sequences, weights),
            "speakers batch features -> batch speakers features",
        )

        if not has_speaker_dimension:
            return output.squeeze(dim=1)

        return output
    

class TSTP(nn.Module):
    """
    Temporal statistics pooling, concatenate mean and std, which is used in
    x-vector
    Comment: simple concatenation can not make full use of both statistics
    """

    def __init__(self, in_dim=0):
        super(TSTP, self).__init__()
        self.in_dim = in_dim
        self.stats_pool = StatsPool()

    def forward(self, features, weights: torch.Tensor = None):
        features = rearrange(
            features,
            "batch dimension channel frames -> batch (dimension channel) frames",
        )

        return self.stats_pool(features, weights=weights)

    def get_out_dim(self):
        self.out_dim = self.in_dim * 2
        return self.out_dim
    
POOLING_LAYERS = {"TSTP": TSTP}

class ResNet(nn.Module):
    def __init__(
            self,
            block,
            num_blocks,
            m_channels=32,
            feat_dim=40,
            embed_dim=128,
            pooling_func="TSTP",
            two_emb_layer=True,
        ):
            super(ResNet, self).__init__()
            self.in_planes = m_channels
            self.feat_dim = feat_dim
            self.embed_dim = embed_dim
            self.stats_dim = int(feat_dim / 8) * m_channels * 8
            self.two_emb_layer = two_emb_layer

            self.conv1 = nn.Conv2d(
                1, m_channels, kernel_size=3, stride=1, padding=1, bias=False
            )
            self.bn1 = nn.BatchNorm2d(m_channels)
            self.layer1 = self._make_layer(block, m_channels, num_blocks[0], stride=1)
            self.layer2 = self._make_layer(block, m_channels * 2, num_blocks[1], stride=2)
            self.layer3 = self._make_layer(block, m_channels * 4, num_blocks[2], stride=2)
            self.layer4 = self._make_layer(block, m_channels * 8, num_blocks[3], stride=2)

            self.pool = POOLING_LAYERS[pooling_func](
                in_dim=self.stats_dim * block.expansion
            )
            self.pool_out_dim = self.pool.get_out_dim()
            self.seg_1 = nn.Linear(self.pool_out_dim, embed_dim)
            if self.two_emb_layer:
                self.seg_bn_1 = nn.BatchNorm1d(embed_dim, affine=False)
                self.seg_2 = nn.Linear(embed_dim, embed_dim)
            else:
                self.seg_bn_1 = nn.Identity()
                self.seg_2 = nn.Identity()

    def _make_layer(self, block, planes, num_blocks, stride):
        strides = [stride] + [1] * (num_blocks - 1)
        layers = []
        for stride in strides:
            layers.append(block(self.in_planes, planes, stride))
            self.in_planes = planes * block.expansion
        return nn.Sequential(*layers)

    def forward(self, x: torch.Tensor, weights: torch.Tensor = None):
        x = x.permute(0, 2, 1) 

        x = x.unsqueeze_(1)
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)

        stats = self.pool(out, weights=weights)

        embed_a = self.seg_1(stats)
        if self.two_emb_layer:
            out = F.relu(embed_a)
            out = self.seg_bn_1(out)
            embed_b = self.seg_2(out)
            return embed_a, embed_b
        else:
            return torch.tensor(0.0), embed_a
        

class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, in_planes, planes, stride=1):
        super(BasicBlock, self).__init__()
        self.conv1 = nn.Conv2d(
            in_planes, planes, kernel_size=3, stride=stride, padding=1, bias=False
        )
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(
            planes, planes, kernel_size=3, stride=1, padding=1, bias=False
        )
        self.bn2 = nn.BatchNorm2d(planes)

        self.shortcut = nn.Sequential()
        if stride != 1 or in_planes != self.expansion * planes:
            self.shortcut = nn.Sequential(
                nn.Conv2d(
                    in_planes,
                    self.expansion * planes,
                    kernel_size=1,
                    stride=stride,
                    bias=False,
                ),
                nn.BatchNorm2d(self.expansion * planes),
            )

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        out = F.relu(out)
        return out
    
def ResNet34(feat_dim, embed_dim, pooling_func="TSTP", two_emb_layer=True):
    return ResNet(
        BasicBlock,
        [3, 4, 6, 3],
        feat_dim=feat_dim,
        embed_dim=embed_dim,
        pooling_func=pooling_func,
        two_emb_layer=two_emb_layer,
    )

class WeSpeakerResNet34(pl.LightningModule):
    def __init__(
        self, 
        sample_rate: int=16000,
        num_channels: int = 1,
        frame_length: int = 25,
        frame_shift: int = 10,
        num_mel_bins: int=80,
        dither: float = 0.0,
        window_type: str = "hamming",
        use_energy: bool = False,
    ):
        super().__init__()
        self.save_hyperparameters(
            "sample_rate",
            "num_channels",
            "num_mel_bins",
            "frame_length",
            "frame_shift",
            "dither",
            "window_type",
            "use_energy",
        )
        self.fbank = partial(
            kaldi.fbank, 
            num_mel_bins=self.hparams.num_mel_bins,
            frame_length=self.hparams.frame_length,
            frame_shift=self.hparams.frame_shift,
            dither=self.hparams.dither,
            sample_frequency=self.hparams.sample_rate,
            window_type=self.hparams.window_type,
            use_energy=self.hparams.use_energy
        )
        self.resnet = ResNet34(
            num_mel_bins, 256, pooling_func="TSTP", two_emb_layer=False
        )
    def compute_fbank(self, waveforms: torch.Tensor) -> torch.Tensor:
        waveforms = waveforms * (1 << 15)   
        features = torch.vmap(self.fbank)(waveforms)

        return features - torch.mean(features, dim=1, keepdim=True)

    def forward(self, waveforms: torch.Tensor,  weights: torch.Tensor=None):
        fbank = self.compute_fbank(waveforms)
        return self.resnet(fbank, weights=weights)[1]


class AgglomerativeClustering():
    def __init__(
        self,
        metric: str="cosine",
        max_num_embeddings: int=1000,
        constrained_assignment: bool=False,
    ):
        self.metric = metric
        self.max_num_embeddings = max_num_embeddings
        self.constrained_assignment = constrained_assignment
        
    def set_num_clusters(
        self,
        num_embeddings: int,
        num_clusters: int=None,
        min_clusters: int=None,
        max_clusters: int=None,
    ):
        min_clusters = num_clusters or min_clusters or 1
        min_clusters = max(1, min(num_embeddings, min_clusters))
        max_clusters = num_clusters or max_clusters or num_embeddings
        max_clusters = max(1, min(num_embeddings, max_clusters))
        
        if min_clusters > max_clusters:
            raise ValueError(
                f"min_clusters must be smaller than (or equal to) max_clusters "
                f"(here: min_clusters={min_clusters:g} and max_clusters={max_clusters:g})."
            )

        if min_clusters == max_clusters:
            num_clusters = min_clusters

        return num_clusters, min_clusters, max_clusters
    
    def cluster(
        self,
        embeddings: np.ndarray,
        min_clusters: int=1,
        max_clusters: int=20,
        num_clusters: int=None,
    ):

        num_embeddings = embeddings.shape[0]
        min_cluster_size = 1
        with np.errstate(divide="ignore", invalid="ignore"):
            embeddings /= np.linalg.norm(embeddings, axis=-1, keepdims=True)
        dendrogram: np.ndarray = linkage(embeddings, method="centroid", metric="euclidean")
        
        clusters = fcluster(dendrogram, 0.8, criterion="distance") - 1
        cluster_unique, cluster_counts = np.unique(clusters, return_counts=True)
        print(cluster_unique, cluster_counts)
        large_clusters = cluster_unique[cluster_counts >= min_cluster_size]
        num_large_clusters = len(large_clusters)
        
        if num_large_clusters < min_clusters:
            num_clusters = min_clusters
        elif num_large_clusters > max_clusters:
            num_clusters = max_clusters
            
        if num_clusters is not None and num_large_clusters != num_clusters:
            _dendrogram = np.copy(dendrogram)
            _dendrogram[:, 2] = np.arange(num_embeddings - 1)

            best_iteration = num_embeddings - 1
            best_num_large_clusters = 1
            
            for iteration in np.argsort(np.abs(dendrogram[:, 2] - self.threshold)):
                new_cluster_size = _dendrogram[iteration, 3]
                if new_cluster_size < min_cluster_size:
                    continue
                
                clusters = fcluster(_dendrogram, iteration, criterion="distance") - 1
                cluster_unique, cluster_counts = np.unique(clusters, return_counts=True)
                large_clusters = cluster_unique[cluster_counts >= min_cluster_size]
                num_large_clusters = len(large_clusters)
                
                if abs(num_large_clusters - num_clusters) < abs(
                    best_num_large_clusters - num_clusters
                ):
                    best_iteration = iteration
                    best_num_large_clusters = num_large_clusters
                
                if num_large_clusters == num_clusters:
                    break
            if best_num_large_clusters != num_clusters:
                clusters = (
                    fcluster(_dendrogram, best_iteration, criterion="distance") - 1
                )
                cluster_unique, cluster_counts = np.unique(clusters, return_counts=True)
                large_clusters = cluster_unique[cluster_counts >= min_cluster_size]
                num_large_clusters = len(large_clusters)
                print(
                    f"Found only {num_large_clusters} clusters. Using a smaller value than {min_cluster_size} for `min_cluster_size` might help."
                )
        if num_large_clusters == 0:
            clusters[:] = 0
            return clusters

        small_clusters = cluster_unique[cluster_counts < min_cluster_size]
        if len(small_clusters) == 0:
            return clusters
        
        large_centroids = np.vstack(
            [
                np.mean(embeddings[clusters == large_k], axis=0)
                for large_k in large_clusters
            ]
        )
        small_centroids = np.vstack(
            [
                np.mean(embeddings[clusters == small_k], axis=0)
                for small_k in small_clusters
            ]
        )
        centroids_cdist = cdist(large_centroids, small_centroids, metric=self.metric)
        for small_k, large_k in enumerate(np.argmin(centroids_cdist, axis=0)):
            clusters[clusters == small_clusters[small_k]] = large_clusters[large_k]
            
        _, clusters = np.unique(clusters, return_inverse=True)
        return clusters


def diarization_process(filename, results, min_speakers=2, max_speakers=15):
    from woa.diarize import WeSpeakerResNet34
    import librosa
    from woa.diarize import AgglomerativeClustering
    import numpy as np
    from huggingface_hub import hf_hub_download

    wespeaker = hf_hub_download(repo_id="pyannote/wespeaker-voxceleb-resnet34-LM", filename="pytorch_model.bin")
    
    embedding_model = WeSpeakerResNet34.load_from_checkpoint(wespeaker, strict=False, map_location='cpu')
    embedding_model.eval()
    embedding_model.to('cpu')

    audio, sr = librosa.load(filename, sr=16000, mono=True)

    tmp_results = results
    results = []
    for result in tmp_results:
        embeddings = []
        for transcript in result[0]["segments"]:
            start, end = transcript["start"], transcript["end"]
            audio_segment = audio[int(start * sr):int(end * sr)]
            audio_segment = torch.Tensor(audio_segment).reshape(1, 1, -1)
            embedding = embedding_model(audio_segment)
            embeddings.append(embedding.detach().numpy())
    
        cluster_model = AgglomerativeClustering()
        cluster_model.set_num_clusters(embedding.shape[0], min_clusters=min_speakers, max_clusters=max_speakers)
        clusters = cluster_model.cluster(np.vstack(embeddings))
        clusters = list(clusters)

        if len(result[0]['segments']) != len(clusters):
            print("Error: number of segments and number of clusters do not match")

        output = {
            'segments': [
                {
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment['text'],
                    'speaker': f"발언자_{clusters.pop(0)}",
                    
                }
                for segment in result[0]['segments']
            ],
        }

    del embedding_model
    
    return output