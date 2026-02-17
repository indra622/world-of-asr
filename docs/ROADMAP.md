# World-of-ASR – Project Roadmap

**Last Updated**: 2026-02-16
**Status**: Active
**Related Docs**: [PROGRESS.md](PROGRESS.md), [ISSUES.md](ISSUES.md)

## Purpose
This document provides a high-level roadmap for the World-of-ASR project, tracking completed phases, current status, and future plans.

---

## Overview

World-of-ASR is a multi-provider speech-to-text platform combining:
- Interactive Gradio UI for offline transcription
- FastAPI backend with async job orchestration
- WebSocket streaming server for real-time transcription
- Multiple ASR provider integrations (local + cloud)

---

## Phase Timeline

```
Phase 1 (✅ Complete)  → Phase 2 (✅ Complete)  → Phase 3 (✅ Complete)  → Phase 4 (📋 Planning)  → Phase 5+ (💡 Future)
  Backend Infrastructure     Model Integration       Async API             Real-time & Scale      Advanced Features
  Jan 2026                   Jan-Feb 2026            Feb 2026              Feb-Mar 2026           Q2 2026+
```

---

## Phase 1: Backend Infrastructure ✅ Complete

**Timeline**: January 2026
**Status**: ✅ Complete
**Completion Report**: `docs/` (archived)

### Goals
- Establish FastAPI backend foundation
- Set up database and ORM layer
- Implement file upload API
- Create basic project structure

### Deliverables
✅ FastAPI application with Uvicorn server
✅ SQLAlchemy ORM with async support (aiosqlite)
✅ Database models: Job, UploadedFile, Result
✅ File upload endpoint with multipart/form-data support
✅ Storage management (uploads/, results/, temp/ directories)
✅ CORS configuration for frontend integration
✅ Basic health check endpoint
✅ Environment configuration with .env support

### Key Technologies
- FastAPI 0.110.0
- SQLAlchemy 2.0.27
- Pydantic 2.6.1
- SQLite (async via aiosqlite)
- Uvicorn ASGI server

---

## Phase 2: Model Integration ✅ Complete

**Timeline**: January-February 2026
**Status**: ✅ Complete
**Completion Report**: `docs/PHASE2_COMPLETION_REPORT.md`

### Goals
- Integrate multiple ASR model providers
- Implement model abstraction layer
- Add caching and optimization
- Support speaker diarization

### Deliverables
✅ ASRModelBase abstract class for provider abstraction
✅ Whisper (origin) integration via whisper-timestamped
✅ Faster-Whisper integration (4x speedup)
✅ NeMo FastConformer integration (Docker-based)
✅ ModelManager singleton with in-memory caching (3-5x performance gain)
✅ DiarizationProcessor using pyannote.audio
✅ Output formatters (VTT, SRT, JSON, TXT, TSV)
✅ Language detection and initial prompt support

### Performance Gains
- Model caching: 3-5x faster for repeated requests
- Faster-Whisper: ~4x faster than original Whisper
- GPU acceleration support (CUDA/cuDNN)

### Key Technologies
- whisper-timestamped
- faster-whisper
- pyannote.audio (speaker diarization)
- torch, torchaudio
- Docker (for NeMo models)

---

## Phase 3: Async Transcription API ✅ Complete

**Timeline**: February 2026
**Status**: ✅ Complete
**Completion Report**: `docs/PHASE3_COMPLETION_REPORT.md`

### Goals
- Non-blocking async transcription
- Job status tracking and progress updates
- Multi-format result generation
- Complete REST API coverage

### Deliverables
✅ Async transcription endpoint (POST /api/v1/transcribe)
✅ BackgroundTasks for non-blocking processing
✅ Job status endpoint with 0-100% progress tracking
✅ Multi-format result downloads (VTT, SRT, JSON, TXT, TSV)
✅ Result summary endpoint
✅ Service layer with business logic separation
✅ Error handling and retry logic
✅ Job lifecycle management (QUEUED → PROCESSING → COMPLETED/FAILED)

### API Endpoints
- `POST /api/v1/upload` - File upload
- `POST /api/v1/transcribe` - Start transcription (202 Accepted)
- `GET /api/v1/transcribe/jobs/{job_id}` - Job status
- `GET /api/v1/results/{job_id}` - Result summary
- `GET /api/v1/results/{job_id}/{format}` - Download results (vtt, srt, json, txt, tsv)
- `GET /health` - Health check with DB verification

### Architecture Decisions
- BackgroundTasks instead of Celery (simpler deployment)
- SQLite for job tracking (sufficient for single-server deployment)
- Per-file progress tracking
- Service layer pattern for testability

---

## Phase 4: Real-time Streaming & Scalability 📋 Planning

**Timeline**: February-March 2026
**Status**: 🚧 In Planning
**Current Progress**: 15%

### Goals
- WebSocket support for real-time transcription
- Job cancellation and priority queues
- Multi-worker scalability
- Enhanced monitoring

### Planned Deliverables

#### 4.1 WebSocket Real-time Streaming 🔄
- [ ] WebSocket endpoint for live audio streaming
- [ ] Integration with existing whisper_streaming module
- [ ] Real-time partial transcription results
- [ ] Session management and reconnection handling
- [ ] Audio format negotiation (PCM, Opus, etc.)

**Dependencies**: ufal/whisper_streaming (already integrated)
**Estimated Effort**: 2-3 weeks
**Blocker**: None

#### 4.2 Job Management Enhancements 📋
- [ ] Job cancellation endpoint (DELETE /api/v1/jobs/{job_id})
- [ ] Priority queue support (express, normal, low)
- [ ] Job scheduling and concurrency limits
- [ ] Batch job submission
- [ ] Job expiration and cleanup

**Dependencies**: None
**Estimated Effort**: 1-2 weeks
**Blocker**: None

#### 4.3 Multi-worker Support 🔧
- [ ] Shared model cache (Redis or filesystem)
- [ ] Worker health monitoring
- [ ] Load balancing strategies
- [ ] GPU affinity and model routing
- [ ] Graceful shutdown handling

**Dependencies**: Redis (optional), Gunicorn
**Estimated Effort**: 2-3 weeks
**Blocker**: None

#### 4.4 Monitoring & Observability 📊
- [ ] Prometheus metrics export
- [ ] Grafana dashboard templates
- [ ] Structured logging (JSON format)
- [ ] Request tracing (OpenTelemetry)
- [ ] Performance profiling hooks

**Dependencies**: prometheus-client, OpenTelemetry
**Estimated Effort**: 1-2 weeks
**Blocker**: None

### Technical Considerations
- **Model Cache**: Current per-process cache doesn't work with multiple workers
  - Solution: Redis-backed shared cache or filesystem cache
- **Database**: SQLite may become bottleneck with high concurrency
  - Consider: PostgreSQL for production deployments
- **WebSocket State**: Need session management for reconnections
  - Solution: Redis-backed session store

### Success Criteria
- ✅ Support 10+ concurrent WebSocket connections
- ✅ Job cancellation with proper cleanup
- ✅ Multi-worker deployment without model duplication
- ✅ Metrics dashboard showing throughput, latency, errors
- ✅ 99.9% uptime with graceful degradation

---

## Phase 5: Provider Expansion 💡 Backlog

**Timeline**: Q2 2026
**Status**: 📝 Backlog (Stubs Ready)
**Current Progress**: 10% (stubs implemented)

### Goals
- Implement external provider adapters
- Add post-processing pipeline
- Support advanced transcription features

### 5.1 External Provider Implementation 🌐

**Priority Order**: Google → Qwen → NVIDIA

#### Google Cloud Speech-to-Text (Priority: High)
- [ ] Implement GoogleSTTProvider adapter
- [ ] Streaming and batch API support
- [ ] Audio format conversion
- [ ] Cost tracking and quota management
- [ ] Error handling and retries

**Status**: Stub ready in `backend/app/core/models/google_stt.py`
**Dependencies**: google-cloud-speech, service account credentials
**Estimated Effort**: 1-2 weeks
**Docs**: `docs/PROVIDERS.md`

#### Alibaba Qwen ASR (Priority: High)
- [ ] Implement QwenASRProvider adapter
- [ ] API authentication and endpoint configuration
- [ ] Forced alignment integration
- [ ] Word-level timing extraction
- [ ] Multi-language support

**Status**: Stub ready in `backend/app/core/models/qwen_asr.py`
**Dependencies**: API key, endpoint access
**Estimated Effort**: 2-3 weeks
**Docs**: `docs/QWEN_ALIGNMENT_PLAN.md`

#### NVIDIA NeMo/Triton/Riva (Priority: Medium)
- [ ] NeMo CTC (offline) implementation
- [ ] NeMo RNNT (streaming) implementation
- [ ] Triton Inference Server integration
- [ ] NVIDIA Riva SDK integration
- [ ] GPU optimization and batching

**Status**: Stubs ready for all NVIDIA providers
**Dependencies**: NVIDIA GPU, Triton server, Riva SDK
**Estimated Effort**: 3-4 weeks
**Docs**: `docs/NVIDIA_INTEGRATION_PLAN.md`

### 5.2 Post-processing Pipeline 🔧

#### Qwen Forced Alignment (Priority: High)
- [ ] Implement QwenForcedAligner processor
- [ ] Word-level timestamp alignment
- [ ] Integration with existing transcription flow
- [ ] Confidence score enrichment

**Status**: Stub ready in `backend/app/core/processors/forced_alignment.py`
**Dependencies**: Qwen API access
**Estimated Effort**: 1-2 weeks

#### Punctuation & Capitalization (Priority: Medium)
- [ ] Implement PnC processor
- [ ] Model selection (local vs API)
- [ ] Multi-language support
- [ ] Integration with transcription pipeline

**Status**: Stub ready in `backend/app/core/processors/pnc.py`
**Dependencies**: PnC model or API
**Estimated Effort**: 1-2 weeks

#### Voice Activity Detection (Priority: Low)
- [ ] Implement VAD processor
- [ ] Audio preprocessing and segmentation
- [ ] Silence trimming
- [ ] Integration with upload pipeline

**Status**: Stub ready in `backend/app/core/processors/vad.py`
**Dependencies**: auditok or silero-vad
**Estimated Effort**: 1 week

### 5.3 Advanced Features 🚀

- [ ] Translation support (transcribe + translate)
- [ ] Custom vocabulary and domain adaptation
- [ ] Multi-channel audio support
- [ ] Speaker identification (beyond diarization)
- [ ] Subtitle synchronization tools
- [ ] API rate limiting and throttling
- [ ] Webhook notifications for job completion

---

## Phase 6: Enterprise Features 💼 Future

**Timeline**: Q3 2026+
**Status**: 💭 Concept Phase

### Potential Features
- Multi-tenancy support with user authentication
- Role-based access control (RBAC)
- API key management and usage analytics
- Custom model fine-tuning support
- Cloud storage integration (S3, GCS, Azure Blob)
- Batch processing pipelines
- Audio quality assessment and enhancement
- Compliance features (GDPR, SOC2)
- White-label deployment options

---

## Critical Dependencies & Blockers

### Current Blockers
1. **Code Quality Issues** (see [ISSUES.md](ISSUES.md))
   - 4 P0 critical issues blocking production deployment
   - 8 P1 high-priority issues causing runtime errors
   - Estimated fix time: 1-2 weeks

2. **Test Coverage**
   - Only 26/46 tests passing
   - 20 tests require GPU/heavy dependencies
   - Need CI/CD improvements

### External Dependencies
- **Hugging Face Token**: Required for pyannote.audio speaker diarization
- **Google Cloud**: Service account for Google STT
- **Qwen API**: API key and endpoint access
- **NVIDIA Hardware**: GPU required for NeMo, Triton, Riva
- **Docker**: Required for NeMo FastConformer

### Technical Debt
- Data model mismatches (ISSUE-006 through ISSUE-009)
- Thread safety issues in streaming client
- Resource leaks in audio handling
- Hardcoded configuration values

---

## Resource Requirements

### Phase 4 (Real-time & Scale)
- **Development**: 1-2 developers, 6-8 weeks
- **Infrastructure**: Redis (optional), load balancer, monitoring stack
- **Testing**: WebSocket load testing, concurrent job testing

### Phase 5 (Provider Expansion)
- **Development**: 1-2 developers, 8-12 weeks
- **API Access**: Google Cloud account, Qwen API, NVIDIA hardware/licenses
- **Testing**: Provider integration tests, cost monitoring

### Phase 6 (Enterprise)
- **Development**: 2-3 developers, 12+ weeks
- **Infrastructure**: Production-grade database (PostgreSQL), auth service
- **Security**: Penetration testing, compliance audits

---

## Success Metrics

### Phase 3 (Current) ✅
- ✅ API response time < 200ms (job submission)
- ✅ Job status updates within 1 second
- ✅ Support 5+ concurrent transcription jobs
- ✅ 5 output formats available

### Phase 4 (Target)
- 🎯 WebSocket latency < 100ms
- 🎯 Support 50+ concurrent connections
- 🎯 Job cancellation response < 500ms
- 🎯 99.9% uptime over 30 days

### Phase 5 (Target)
- 🎯 3+ external providers functional
- 🎯 Post-processing adds < 10% overhead
- 🎯 Qwen alignment accuracy > 95%
- 🎯 Provider failover < 5 seconds

---

## Decision Log

### Architecture Decisions

**2026-01**: **FastAPI over Flask**
- Rationale: Native async/await support, automatic OpenAPI docs, better performance
- Status: ✅ Validated

**2026-01**: **SQLite over PostgreSQL (Phase 1-3)**
- Rationale: Simpler deployment, sufficient for single-server, async support
- Status: ✅ Adequate for current scale
- Future: Consider PostgreSQL for Phase 4+ (multi-worker)

**2026-02**: **BackgroundTasks over Celery**
- Rationale: Simpler deployment, no broker required, adequate for scale
- Status: ✅ Working well
- Future: May need Celery for Phase 4 distributed workers

**2026-02**: **Per-format Result columns over JSON dict**
- Rationale: Better query performance, explicit schema, easier validation
- Status: ✅ Implemented
- Trade-off: Less flexible, more columns

### Provider Priority

**2026-02**: **Local models first (Whisper, Faster-Whisper)**
- Rationale: No external dependencies, no API costs, privacy-friendly
- Status: ✅ Complete

**2026-02**: **Google STT before Qwen**
- Rationale: Better documentation, more stable API, wider adoption
- Status: 📋 Planned for Phase 5

**2026-02**: **NVIDIA integration lowest priority**
- Rationale: Hardware requirements, complexity, licensing considerations
- Status: 📋 Backlog (stubs ready)

---

## Risk Assessment

### High Risk
- **Resource Leaks** (ISSUE-003): Could cause production crashes → P0 fix required
- **Thread Safety** (ISSUE-004): Race conditions in streaming → P0 fix required
- **Data Model Mismatches** (ISSUE-006-009): Runtime errors in API → P1 fix required

### Medium Risk
- **Multi-worker Deployment**: Model cache per-process → Redis solution planned
- **SQLite Scalability**: May need PostgreSQL for > 100 concurrent users
- **External Provider Costs**: API usage could become expensive → need monitoring

### Low Risk
- **Dependency Updates**: Regular maintenance required
- **Documentation Drift**: Need to keep docs synchronized with code
- **Test Coverage**: Need to expand coverage to 70%+

---

## Review Schedule

- **Weekly**: Progress check on current phase
- **Monthly**: Roadmap review and priority adjustment
- **Quarterly**: Major phase transitions and resource planning

---

## Conclusion

World-of-ASR has successfully completed 3 phases and established a solid foundation for speech-to-text processing. The project is currently between Phase 3 and Phase 4, with core functionality production-ready for local deployments.

**Current Focus**:
1. Resolve P0/P1 critical issues (1-2 weeks)
2. Plan and implement Phase 4 (real-time streaming, scalability)
3. Begin Phase 5 provider expansion (Google, Qwen)

**Long-term Vision**:
A flexible, multi-provider ASR platform supporting both offline and real-time transcription with advanced post-processing capabilities, suitable for both local and cloud deployment.

---

**Next Review**: 2026-03-01
