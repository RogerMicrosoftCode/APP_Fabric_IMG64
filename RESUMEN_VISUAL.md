# 📊 Resumen Visual y Quick Reference

> **Guía Visual Rápida de la Arquitectura de Gestión de Imágenes**

---

## 🎯 Comparativa: Antes vs. Después

### Arquitectura Actual (Base64)

```
┌─────────────────────────────────────────────────────────────┐
│                    SuccessFactors API                        │
│                            │                                 │
│                            ▼                                 │
│                    [Pipeline Notebook]                       │
│                            │                                 │
│                            ▼                                 │
│    ┌────────────────────────────────────────┐               │
│    │   Delta Table: employees               │               │
│    ├────────────────────────────────────────┤               │
│    │ employee_id  │ PhotoBase64 (STRING)    │  ◀── PROBLEMA │
│    │ 102025       │ /9j/4AAQSkZJRg...       │      2.5GB    │
│    │ 102026       │ iVBORw0KGgoAAAAN...     │      Tabla    │
│    └────────────────────────────────────────┘               │
│                            │                                 │
│                            ▼                                 │
│              [HTML Generation in Notebook]                   │
│                            │                                 │
│                            ▼                                 │
│    ┌────────────────────────────────────────┐               │
│    │  content_table (Delta)                 │               │
│    │  - photo_html (HTML con base64 embed)  │               │
│    └────────────────────────────────────────┘               │
│                            │                                 │
│                            ▼                                 │
│              [Fabric Data Agent / Workbook]                  │
│                                                              │
│  ⚠️ PROBLEMAS:                                               │
│  • Storage cost: $0.18/GB = $450/año                        │
│  • Query latency: 250ms                                     │
│  • Table size limit: 2GB max                                │
│  • No versioning                                            │
│  • No caching                                               │
│  • No governance                                            │
└─────────────────────────────────────────────────────────────┘
```

### Arquitectura Propuesta (Files + Metadata)

```
┌──────────────────────────────────────────────────────────────────────┐
│                        SuccessFactors API                             │
│                                │                                      │
│                                ▼                                      │
│                       [Pipeline Notebook]                             │
│                        ┌──────┴──────┐                               │
│                        │             │                               │
│                        ▼             ▼                               │
│          ┌─────────────────┐   ┌──────────────────┐                 │
│          │ Lakehouse Files │   │ Delta: Registry  │                 │
│          ├─────────────────┤   ├──────────────────┤                 │
│          │ 📁 2026/03/     │   │ photo_id         │                 │
│          │  102025.jpg     │◀──│ employee_id      │                 │
│          │  102025_t.jpg   │   │ photo_url ───────┼─────┐           │
│          │  ...            │   │ thumbnail_url    │     │           │
│          │                 │   │ classification   │     │           │
│          │ 💰 $27/año      │   │ is_active        │     │           │
│          └─────────────────┘   │ version          │     │           │
│                                │                  │     │           │
│                                │ 💰 $60/año       │     │           │
│                                └──────────────────┘     │           │
│                                        │                │           │
│                                        ▼                │           │
│                          ┌──────────────────────┐       │           │
│                          │ Content Table        │       │           │
│                          │ (Materialized)       │       │           │
│                          │ - HTML with URLs     │       │           │
│                          │ - Metadata JSON      │       │           │
│                          └──────────────────────┘       │           │
│                                        │                │           │
│                        ┌───────────────┴────┐           │           │
│                        ▼                    ▼           │           │
│              [Workbooks]          [AI Agents]           │           │
│                        │                    │           │           │
│                        └────────┬───────────┘           │           │
│                                 ▼                       │           │
│                        [FabricImageAgentAPI]            │           │
│                                 │                       │           │
│                        ┌────────┴────────┐              │           │
│                        ▼                 ▼              │           │
│                  [Redis Cache]    [OneLake Files] ◀─────┘           │
│                   ⚡ <50ms             ⚡ <150ms                      │
│                                                                      │
│  ✅ BENEFICIOS:                                                      │
│  • Storage cost: $87/año (-81%)                                     │
│  • Query latency: 50ms (-80%)                                       │
│  • Scalability: Ilimitada                                           │
│  • Versioning: Sí                                                   │
│  • Caching: Redis (hit rate >80%)                                   │
│  • Governance: RLS + ABAC + Purview                                 │
│  • Multi-channel: Workbooks + Agents + APIs                         │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 📈 KPIs: Estado Actual vs. Target

### Performance

```
Query Latency (P95)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Actual:  ████████████████████████░░░░░░░░░░░  250ms  ❌
Target:  ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   50ms  ✅
                                            -80%


Workbook Load Time
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Actual:  ████████████████████████████████████  5.2s   ❌
Target:  ███████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  2.0s   ✅
                                            -62%


Agent Response Time
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Actual:  ██████████████████████████████░░░░░░  3.1s   ❌
Target:  ███████████░░░░░░░░░░░░░░░░░░░░░░░░░  2.0s   ✅
                                            -35%


Cache Hit Rate
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Actual:  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   0%    ❌
Target:  ████████████████████████████████░░░░  80%    ✅
                                            +80%
```

### Costos

```
Storage Cost (Annual)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Actual:  ████████████████████████████████████  $450   ❌
Target:  ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   $87   ✅
                                            -81%


Total Monthly Cost
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Actual:  ████████████████████████████████░░░░  $416   
Target:  ████████████████████████████████████  $452   
                                             +9%

⚠️ Nota: +9% en costos totales pero ROI 260% por mejoras en performance
```

### Governance

```
Production Readiness Score
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Actual:  ████████████████░░░░░░░░░░░░░░░░░░░░  45%    ❌
Target:  ████████████████████████████████████  90%    ✅
                                            +45%

Security:       45% ──▶ 90%
Performance:    30% ──▶ 95%
Reliability:    40% ──▶ 90%
Operations:     50% ──▶ 85%
Testing:        60% ──▶ 90%
```

---

## 🗺️ Roadmap Visual de 5 Semanas

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         5-WEEK IMPLEMENTATION ROADMAP                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Week 1-2: SPRINT 1 - FOUNDATION                                       │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  Mon  │  Tue  │  Wed  │  Thu  │  Fri  │  Mon  │  Tue  │  Wed   │    │
│  ├───────┼───────┼───────┼───────┼───────┼───────┼───────┼────────┤    │
│  │ Setup │ Files │Migrate│ RLS   │Content│ Work  │ UAT   │ Review │    │
│  │ Env   │Struct │Data   │Config │Table  │book   │ Test  │Sprint  │    │
│  └────────────────────────────────────────────────────────────────┘    │
│          ✓ Deliverable: Workbooks showing photos                        │
│          ✓ Checkpoint: Migration success rate >99%                      │
│                                                                          │
│  Week 3-4: SPRINT 2 - AGENT INTEGRATION                                │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  Thu  │  Fri  │  Mon  │  Tue  │  Wed  │  Thu  │  Fri  │  Mon   │    │
│  ├───────┼───────┼───────┼───────┼───────┼───────┼───────┼────────┤    │
│  │ API   │ Redis │ Agent │Audit  │Perf   │Load   │ UAT   │ Review │    │
│  │Design │Cache  │Integr │Log    │Tuning │Test   │Agent  │Sprint  │    │
│  └────────────────────────────────────────────────────────────────┘    │
│          ✓ Deliverable: AI Agents consuming photos via API              │
│          ✓ Checkpoint: Latency P95 <100ms                               │
│                                                                          │
│  Week 5: SPRINT 3 - GOVERNANCE & GO-LIVE                               │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  Tue  │  Wed  │  Thu  │  Fri  │  Mon  │                        │    │
│  ├───────┼───────┼───────┼───────┼───────┤                        │    │
│  │ ABAC  │Purview│Monitor│ DR    │Go/NoGo│   🚀 GO-LIVE 🚀       │    │
│  │Policy │Setup  │Alerts │Drill  │Meeting│                        │    │
│  └────────────────────────────────────────────────────────────────┘    │
│          ✓ Deliverable: Production-ready system                         │
│          ✓ Checkpoint: Readiness score >90%                             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

Legend:
  ✓ = Completed
  ⏳ = In Progress
  ◯ = Not Started
```

---

## 🏗️ Arquitectura de 3 Capas Simplificada

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CAPA DE PRESENTACIÓN                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐              │
│  │  Workbooks  │   │ AI Agents   │   │ Power BI    │              │
│  │             │   │             │   │             │              │
│  │  📊 HTML    │   │  🤖 Chat    │   │  📈 Reports │              │
│  │  Rendering  │   │  Interface  │   │  Visuals    │              │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘              │
│         │                 │                 │                      │
└─────────┼─────────────────┼─────────────────┼──────────────────────┘
          │                 │                 │
┌─────────┼─────────────────┼─────────────────┼──────────────────────┐
│         │                 │                 │                      │
│         │      CAPA DE LÓGICA DE NEGOCIO / API                     │
├─────────┴─────────────────┴─────────────────┴──────────────────────┤
│                                                                      │
│    ┌──────────────────────────────────────────────────────────┐    │
│    │          FabricImageAgentAPI (REST)                       │    │
│    │  ┌─────────────────────────────────────────────────────┐ │    │
│    │  │  • get_employee_photo(employee_id)                   │ │    │
│    │  │  • search_employees_with_photos(query)               │ │    │
│    │  │  • get_batch_photos(employee_ids[])                  │ │    │
│    │  └─────────────────────────────────────────────────────┘ │    │
│    └──────────────────────┬───────────────────────────────────┘    │
│                           │                                         │
│                ┌──────────┴──────────┐                              │
│                ▼                     ▼                              │
│    ┌────────────────────┐  ┌────────────────────┐                  │
│    │   Redis Cache      │  │  Security Layer    │                  │
│    │   - Metadata       │  │  - Authentication  │                  │
│    │   - TTL: 1 hour    │  │  - Authorization   │                  │
│    │   - Hit rate: 80%  │  │  - RLS/ABAC        │                  │
│    └────────────────────┘  └────────────────────┘                  │
│                                                                      │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
┌──────────────────────────────┴───────────────────────────────────────┐
│                                                                       │
│                      CAPA DE DATOS Y ALMACENAMIENTO                  │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                    Microsoft OneLake                            │  │
│  │  ┌────────────────────────┐  ┌───────────────────────────────┐ │  │
│  │  │   Lakehouse Files      │  │   Delta Tables                 │ │  │
│  │  ├────────────────────────┤  ├───────────────────────────────┤ │  │
│  │  │ 📁 employee_photos/    │◀─│ 📊 employee_photo_registry    │ │  │
│  │  │   ├─ 2026/03/          │  │    - photo_id (PK)            │ │  │
│  │  │   │  ├─ 102025.jpg     │  │    - employee_id              │ │  │
│  │  │   │  └─ 102025_t.jpg   │  │    - photo_url ──────────────┼─┼─┐│
│  │  │   └─ archive/          │  │    - thumbnail_url            │ │ ││
│  │  │                        │  │    - classification (PII)     │ │ ││
│  │  │ Storage: Hot/Warm/Cold │  │    - is_active                │ │ ││
│  │  │ Cost: $0.023/GB        │  │    - version                  │ │ ││
│  │  └────────────────────────┘  │                               │ │ ││
│  │                               │ 📊 workbook_employee_content  │ │ ││
│  │  ┌────────────────────────┐  │    - employee_id              │ │ ││
│  │  │   Audit & Governance   │  │    - photo_html               │ │ ││
│  │  ├────────────────────────┤  │    - metadata_json            │ │ ││
│  │  │ 📋 photo_access_audit  │  │                               │ │ ││
│  │  │ 🏷️ Microsoft Purview   │  │ Optimizations:                │ │ ││
│  │  │ 🔒 Row-Level Security  │  │ - ZORDER(employee_id)         │ │ ││
│  │  │ 🎭 ABAC Policies       │  │ - Auto-Optimize: ON           │ │ ││
│  │  └────────────────────────┘  └───────────────────────────────┘ │ ││
│  └────────────────────────────────────────────────────────────────┘  ││
│         ▲                                                             ││
│         │                                                             ││
│         └─────────────────────────────────────────────────────────────┘│
│                          OneLake URL Reference                         │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 💡 Quick Decision Tree: "¿Debo implementar X feature?"

```
Start: Feature Request
        │
        ▼
    ┌───────────────────────┐
    │ ¿Es requerido para    │
    │ cumplir compliance?   │───YES───▶ PRIORIDAD 🔴 CRÍTICA
    └─────────┬─────────────┘
              │ NO
              ▼
    ┌───────────────────────┐
    │ ¿Bloquea AI Agents    │
    │ o Workbooks?          │───YES───▶ PRIORIDAD 🔴 CRÍTICA
    └─────────┬─────────────┘
              │ NO
              ▼
    ┌───────────────────────┐
    │ ¿Mejora performance   │
    │ >30%?                 │───YES───▶ PRIORIDAD 🟡 ALTA
    └─────────┬─────────────┘
              │ NO
              ▼
    ┌───────────────────────┐
    │ ¿ROI >200% en 1 año?  │───YES───▶ PRIORIDAD 🟡 ALTA
    └─────────┬─────────────┘
              │ NO
              ▼
    ┌───────────────────────┐
    │ ¿Mejora UX            │
    │ significativamente?   │───YES───▶ PRIORIDAD 🟢 MEDIA
    └─────────┬─────────────┘
              │ NO
              ▼
          BACKLOG (evaluar post go-live)
```

---

## 📊 Matriz de Decisión: Storage Tiers

```
┌─────────────────────────────────────────────────────────────────────┐
│                    STORAGE TIER DECISION MATRIX                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Criterio                   │  HOT     │  WARM    │  COLD           │
│  ───────────────────────────┼──────────┼──────────┼───────────────  │
│  Frecuencia de Acceso       │  Diaria  │  Mensual │  Anual          │
│  Latencia Requerida         │  <50ms   │  <200ms  │  <5s            │
│  Costo por GB/mes           │  $0.023  │  $0.015  │  $0.008         │
│  Caso de Uso                │  Activos │  Reciente│  Histórico      │
│  Retention                  │  6 meses │  12 meses│  7 años         │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  RECOMMENDATION ENGINE:                                     │     │
│  │                                                             │     │
│  │  IF last_accessed < 180 days THEN move_to_warm()          │     │
│  │  IF last_accessed < 540 days THEN move_to_cold()          │     │
│  │  IF employee.is_active = FALSE AND tenure > 2y             │     │
│  │     THEN archive_immediately()                             │     │
│  └────────────────────────────────────────────────────────────┘     │
│                                                                      │
│  EJEMPLO DE DISTRIBUCIÓN (10,000 empleados):                        │
│                                                                      │
│  🔥 HOT  (6,000 fotos): $138/mes                                    │
│  ██████████████████████████████████████                             │
│                                                                      │
│  ❄️ WARM (2,500 fotos): $37.50/mes                                 │
│  ████████████████                                                   │
│                                                                      │
│  🧊 COLD (1,500 fotos): $12/mes                                     │
│  ██████████                                                         │
│                                                                      │
│  TOTAL: $187.50/mes vs $230/mes (all-hot) = SAVE 18%               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Performance Optimization Checklist

```
┌─────────────────────────────────────────────────────────────────┐
│               PERFORMANCE OPTIMIZATION CHECKLIST                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [ ] QUERY OPTIMIZATION                                         │
│   ✓ ZORDER BY (employee_id)                                    │
│   ✓ Partition pruning enabled                                  │
│   ✓ Predicate pushdown to storage                              │
│   ✓ Column statistics updated                                  │
│   ✓ OPTIMIZE ran weekly                                        │
│                                                                  │
│  [ ] CACHING STRATEGY                                           │
│   ✓ Redis L3 cache (metadata)                                  │
│   ✓ CDN L2 cache (images)                                      │
│   ✓ Browser L1 cache (5 min)                                   │
│   ✓ Cache hit rate >80%                                        │
│   ✓ Invalidation on update                                     │
│                                                                  │
│  [ ] IMAGE OPTIMIZATION                                         │
│   ✓ Thumbnails generated (150x150)                             │
│   ✓ Lazy loading implemented                                   │
│   ✓ Progressive rendering                                      │
│   ✓ Format: JPEG (quality 85)                                  │
│   ✓ Max size: 1024x1024                                        │
│                                                                  │
│  [ ] NETWORK OPTIMIZATION                                       │
│   ✓ HTTP/2 enabled                                             │
│   ✓ Compression (gzip/brotli)                                  │
│   ✓ Connection pooling                                         │
│   ✓ Keep-alive headers                                         │
│   ✓ CDN geo-distribution                                       │
│                                                                  │
│  [ ] API OPTIMIZATION                                           │
│   ✓ Batch requests supported                                   │
│   ✓ Pagination implemented                                     │
│   ✓ Rate limiting (100/min)                                    │
│   ✓ Response compression                                       │
│   ✓ Async operations                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

TARGET METRICS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Single Photo Load:        <100ms   ████████████░░░░░░░░
Workbook Full Render:     <2s      ████████████████████
Agent Response (w/photo): <2s      ████████████████████
Batch 20 Photos:          <1s      ████████████████████
Cache Hit Rate:           >80%     ████████████████████████
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🔒 Security Layers Visualization

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEFENSE IN DEPTH SECURITY                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Layer 7 │ ┌────────────────────────────────────────────┐      │
│  APP     │ │ Application Security                        │      │
│          │ │ • Input validation                          │      │
│          │ │ • SQL injection prevention                  │      │
│          │ │ • XSS protection                            │      │
│          │ └────────────────────────────────────────────┘      │
│                                   │                             │
│  Layer 6 │ ┌────────────────────────────────────────────┐      │
│  DATA    │ │ Data Masking & Classification               │      │
│          │ │ • Dynamic data masking                      │      │
│          │ │ • PII classification (Purview)              │      │
│          │ │ • ABAC based on labels                      │      │
│          │ └────────────────────────────────────────────┘      │
│                                   │                             │
│  Layer 5 │ ┌────────────────────────────────────────────┐      │
│  ACCESS  │ │ Row-Level Security (RLS)                    │      │
│          │ │ • Department filtering                      │      │
│          │ │ • Manager hierarchy                         │      │
│          │ │ • Self-service access                       │      │
│          │ └────────────────────────────────────────────┘      │
│                                   │                             │
│  Layer 4 │ ┌────────────────────────────────────────────┐      │
│  AUTHZ   │ │ Authorization (RBAC)                        │      │
│          │ │ • HR Admin (full access)                    │      │
│          │ │ • HR Manager (department)                   │      │
│          │ │ • Employee (self)                           │      │
│          │ └────────────────────────────────────────────┘      │
│                                   │                             │
│  Layer 3 │ ┌────────────────────────────────────────────┐      │
│  AUTHN   │ │ Authentication (Entra ID)                   │      │
│          │ │ • MFA required                              │      │
│          │ │ • Conditional access policies               │      │
│          │ │ • Token validation                          │      │
│          │ └────────────────────────────────────────────┘      │
│                                   │                             │
│  Layer 2 │ ┌────────────────────────────────────────────┐      │
│  NETWORK │ │ Transport Security                          │      │
│          │ │ • TLS 1.3                                   │      │
│          │ │ • Certificate pinning                       │      │
│          │ │ • Encrypted in transit                      │      │
│          │ └────────────────────────────────────────────┘      │
│                                   │                             │
│  Layer 1 │ ┌────────────────────────────────────────────┐      │
│  STORAGE │ │ Encryption at Rest                          │      │
│          │ │ • AES-256                                   │      │
│          │ │ • Key Vault managed keys                    │      │
│          │ │ • Auto key rotation                         │      │
│          │ └────────────────────────────────────────────┘      │
│                             ▼                                   │
│                      ┌────────────┐                             │
│                      │  Audit Log │                             │
│                      │  (All Layers)                            │
│                      └────────────┘                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Success Metrics Dashboard (Template)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    KEY PERFORMANCE INDICATORS (KPIs)                 │
│                         Week 1 Post Go-Live                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  🟢 UPTIME                                                           │
│  ████████████████████████████████████████████████ 99.87%           │
│  Target: 99.5%  ✅ ABOVE TARGET                                     │
│                                                                      │
│  🔵 QUERY LATENCY (P95)                                              │
│  ████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 87ms             │
│  Target: <100ms  ✅ ON TARGET                                        │
│                                                                      │
│  🟡 CACHE HIT RATE                                                   │
│  ████████████████████████████████████░░░░░░░░░░░░ 83%              │
│  Target: >75%  ✅ ABOVE TARGET                                       │
│                                                                      │
│  🟣 ERRORS (% of requests)                                           │
│  █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 0.4%             │
│  Target: <2%  ✅ ON TARGET                                           │
│                                                                      │
│  🔴 USER SATISFACTION                                                │
│  ████████████████████████████████████░░░░░░░░░░░░ 4.3/5            │
│  Target: >4.0  ✅ ON TARGET                                          │
│                                                                      │
│  💰 STORAGE COST (Monthly)                                           │
│  ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ $28.50           │
│  Budget: <$45  ✅ UNDER BUDGET                                       │
│                                                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  OVERALL HEALTH:  ✅ EXCELLENT (5/6 KPIs met)                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📞 Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────┐
│        MICROSOFT FABRIC IMAGE ARCHITECTURE - QUICK REF          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📁 PRIMARY STORAGE LOCATION                                    │
│  Files/employee_photos/YYYY/MM/{employee_id}_profile.jpg        │
│                                                                  │
│  📊 METADATA REGISTRY                                           │
│  Table: hr_lakehouse.employee_photo_registry                    │
│  Key: employee_id                                               │
│  Partitioned by: upload_timestamp                               │
│                                                                  │
│  🔌 API ENDPOINT                                                │
│  GET /api/v1/employees/{id}/photo                               │
│  Response: { photo_url, thumbnail_url, metadata }               │
│                                                                  │
│  📈 WORKBOOK TABLE                                              │
│  Table: hr_lakehouse.workbook_employee_content                  │
│  Contains: photo_html (pre-rendered)                            │
│                                                                  │
│  ⚡ PERFORMANCE TARGETS                                          │
│  Query Latency:    <100ms (P95)                                 │
│  Cache Hit Rate:   >80%                                         │
│  Uptime:           >99.9%                                       │
│                                                                  │
│  🔒 SECURITY                                                     │
│  Auth: Microsoft Entra ID                                       │
│  RLS: Department-based filtering                                │
│  ABAC: Classification-based (PII)                               │
│  Audit: 100% coverage                                           │
│                                                                  │
│  💰 COST OPTIMIZATION                                            │
│  Hot Tier:  <6 months, $0.023/GB                               │
│  Warm Tier: 6-18 mo, $0.015/GB                                 │
│  Cold Tier: 18+ mo, $0.008/GB                                  │
│                                                                  │
│  📞 SUPPORT CONTACTS                                            │
│  L1 Support:  fabric-support@contoso.com                        │
│  Escalation:  fabric-oncall (Slack)                             │
│  Architect:   fabric-architecture@contoso.com                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚨 Common Issues & Quick Fixes

| Issue | Symptom | Quick Fix |
|-------|---------|-----------|
| **Photo not loading** | 404 error | Check `is_active=TRUE` and `is_current_version=TRUE` |
| **Slow query** | Latency >200ms | Run `OPTIMIZE table ZORDER BY (employee_id)` |
| **Cache not working** | Hit rate <50% | Verify Redis connection, check TTL config |
| **Access denied** | 403 error | Verify RLS policy, check user in correct department |
| **Broken image link** | OneLake URL 404 | Re-run pipeline to regenerate URLs |
| **Pipeline failure** | Upload errors | Check SuccessFactors API credentials in Key Vault |

---

*Document generated automatically - Last updated: 2026-03-03*  
*For full documentation, see: ANALISIS_TECNICO_ARQUITECTURA.md*
