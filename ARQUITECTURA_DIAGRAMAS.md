# 📐 Diagramas de Arquitectura Detallados

> **Documentación Visual de la Arquitectura de Gestión de Imágenes en Microsoft Fabric**

---

## 📑 Índice de Diagramas

1. [Arquitectura End-to-End Completa](#1-arquitectura-end-to-end-completa)
2. [Pipeline de Ingesta desde SuccessFactors](#2-pipeline-de-ingesta-desde-successfactors)
3. [Arquitectura de Almacenamiento](#3-arquitectura-de-almacenamiento)
4. [Flujo de Consumo por Workbooks](#4-flujo-de-consumo-por-workbooks)
5. [Flujo de Consumo por Agentes IA](#5-flujo-de-consumo-por-agentes-ia)
6. [Arquitectura de Seguridad y Governance](#6-arquitectura-de-seguridad-y-governance)
7. [Alta Disponibilidad y Disaster Recovery](#7-alta-disponibilidad-y-disaster-recovery)
8. [Flujo de Datos con Optimización](#8-flujo-de-datos-con-optimización)

---

## 1. Arquitectura End-to-End Completa

```mermaid
graph TB
    subgraph "Capa de Origen"
        SF[SAP SuccessFactors<br/>📊 Employee Master Data<br/>📷 Profile Photos API]
    end
    
    subgraph "Capa de Ingesta y Procesamiento"
        DP[Data Pipeline<br/>⚙️ Fabric Notebook<br/>🔄 Scheduled Execution]
        DP --> VAL{Validación<br/>de Imagen}
        VAL -->|❌ Inválida| ERR[Error Handler<br/>📝 Log & Alert]
        VAL -->|✅ Válida| PROC[Procesador de Imagen]
        PROC --> RESIZE[Redimensionar<br/>Max: 1024x1024]
        PROC --> THUMB[Generar Thumbnail<br/>150x150px]
        PROC --> META[Extraer Metadata<br/>Dimensiones, Formato, Tamaño]
    end
    
    subgraph "Capa de Almacenamiento - Microsoft OneLake"
        direction TB
        subgraph LH[Lakehouse: hr_lakehouse]
            direction LR
            subgraph FILES[📁 Files Section]
                ORIG[employee_photos/<br/>YYYY/MM/<br/>empID_profile.jpg]
                THUMBS[employee_photos/<br/>YYYY/MM/<br/>empID_profile_thumb.jpg]
                ARCHIVE[employee_photos/<br/>archive/<br/>empID_vN.jpg]
            end
            
            subgraph TABLES[📊 Tables Section]
                REG[employee_photo_registry<br/>🔑 Delta Table<br/>Metadata + URLs]
                CONTENT[workbook_employee_content<br/>📄 Delta Table<br/>HTML + JSON]
                AUDIT[photo_access_audit<br/>📋 Delta Table<br/>Access Logs]
            end
        end
    end
    
    subgraph "Capa de API y Servicios"
        API[FabricImageAgentAPI<br/>🔌 REST Endpoints<br/>🔐 Authentication]
        CACHE[Redis Cache Layer<br/>⚡ TTL: 1 hour<br/>📦 Metadata Only]
        SAS[SAS Token Generator<br/>🔑 Time-limited URLs<br/>⏱️ Valid: 1 hour]
    end
    
    subgraph "Capa de Consumo"
        WB[Microsoft Fabric Workbook<br/>📊 Interactive Dashboards<br/>🖼️ HTML Image Rendering]
        AG[AI Agents<br/>🤖 Fabric Data Agent<br/>💬 Chat Interface<br/>🧠 Context-aware]
        PWRBI[Power BI Reports<br/>📈 Analytics<br/>📊 KPI Dashboards]
        EXT[External Apps<br/>🌐 Web/Mobile<br/>🔌 API Integration]
    end
    
    subgraph "Capa de Seguridad y Governance"
        ENTRA[Microsoft Entra ID<br/>👤 Authentication<br/>🔐 Authorization]
        RLS[Row-Level Security<br/>🔒 Department-based<br/>📂 Data Filtering]
        ABAC[Attribute-Based Access<br/>🏷️ Classification-based<br/>🎭 Role-based]
        PURVIEW[Microsoft Purview<br/>📜 Data Catalog<br/>🔍 Lineage Tracking<br/>🏷️ Classification]
        KV[Azure Key Vault<br/>🔑 Secrets Management<br/>🔐 API Keys]
    end
    
    subgraph "Capa de Monitoreo y Observabilidad"
        APPINS[Application Insights<br/>📊 Telemetry<br/>⚠️ Alerts<br/>📈 Metrics]
        LOGS[Log Analytics<br/>📝 Centralized Logs<br/>🔍 KQL Queries]
        DASH[Monitoring Dashboards<br/>📊 KPI Visualization<br/>⏱️ Real-time Metrics]
    end
    
    %% Flujo de Datos
    SF -->|OData API| DP
    RESIZE --> ORIG
    THUMB --> THUMBS
    META --> REG
    ORIG -.->|OneLake URL| REG
    THUMBS -.->|OneLake URL| REG
    REG -->|JOIN| CONTENT
    
    %% Consumo
    CONTENT -->|Query| WB
    REG -->|API Call| API
    API -->|Check| CACHE
    CACHE -->|Miss| REG
    API -->|Generate| SAS
    SAS --> AG
    SAS --> EXT
    CONTENT -->|DirectQuery| PWRBI
    
    %% Seguridad
    ENTRA -.->|Auth| WB
    ENTRA -.->|Auth| AG
    ENTRA -.->|Auth| API
    RLS -.->|Filter| CONTENT
    ABAC -.->|Filter| REG
    KV -.->|Provide Secrets| DP
    REG -.->|Metadata| PURVIEW
    CONTENT -.->|Metadata| PURVIEW
    
    %% Auditoría
    WB -.->|Log Access| AUDIT
    AG -.->|Log Access| AUDIT
    API -.->|Log Access| AUDIT
    AUDIT -.->|Events| APPINS
    DP -.->|Telemetry| APPINS
    APPINS --> LOGS
    LOGS --> DASH
    
    %% Estilos
    style SF fill:#0078D4,color:#fff,stroke:#005a9e,stroke-width:3px
    style LH fill:#50E6FF,color:#000,stroke:#00b7c3,stroke-width:3px
    style WB fill:#7FBA00,color:#fff,stroke:#5e8700,stroke-width:3px
    style AG fill:#7FBA00,color:#fff,stroke:#5e8700,stroke-width:3px
    style ENTRA fill:#FFB900,color:#000,stroke:#d39300,stroke-width:3px
    style PURVIEW fill:#FFB900,color:#000,stroke:#d39300,stroke-width:3px
    style CACHE fill:#E81123,color:#fff,stroke:#c50f1f,stroke-width:2px
```

---

## 2. Pipeline de Ingesta desde SuccessFactors

```mermaid
sequenceDiagram
    participant SF as SuccessFactors API
    participant SCH as Fabric Scheduler
    participant NB as Pipeline Notebook
    participant KV as Key Vault
    participant VAL as Validator
    participant PROC as Image Processor
    participant FS as Lakehouse Files
    participant DT as Delta Table
    participant AL as Alert System
    participant MON as Monitoring
    
    SCH->>NB: Trigger Pipeline (Daily 2 AM)
    NB->>KV: Get API Credentials
    KV-->>NB: Return Secrets
    
    NB->>SF: Request Employee List
    SF-->>NB: Return Employee IDs
    
    loop For Each Employee
        NB->>SF: GET /Photo?userId={id}
        SF-->>NB: Return Image Binary
        
        NB->>VAL: Validate Image
        alt Valid Image
            VAL-->>NB: ✅ Valid
            NB->>PROC: Process Image
            
            par Parallel Processing
                PROC->>PROC: Resize to 1024x1024
                PROC->>PROC: Generate Thumbnail 150x150
                PROC->>PROC: Extract Metadata
            end
            
            PROC->>FS: Save Original Image
            PROC->>FS: Save Thumbnail
            FS-->>PROC: Return OneLake URLs
            
            PROC->>DT: Insert Metadata Record
            DT-->>PROC: ✅ Success
            
            PROC->>MON: Log Success Metric
        else Invalid Image
            VAL-->>NB: ❌ Invalid
            NB->>AL: Send Alert
            NB->>MON: Log Error Metric
        end
    end
    
    NB->>DT: Run OPTIMIZE + ZORDER
    NB->>MON: Pipeline Completed
    MON->>AL: Check SLA (Success Rate > 95%)
    
    alt SLA Met
        AL-->>SCH: ✅ Pipeline Success
    else SLA Breach
        AL->>AL: Send Critical Alert
        AL-->>SCH: ⚠️ Pipeline Warning
    end
```

---

## 3. Arquitectura de Almacenamiento

```mermaid
graph TB
    subgraph "Lakehouse Storage Architecture"
        direction TB
        
        subgraph HOT["🔥 Hot Tier (Recent 6 months)"]
            direction LR
            H_CURR[Current Photos<br/>employee_photos/2026/03/]
            H_PREV[Previous Months<br/>employee_photos/2026/01-02/]
            H_CURR -.->|Auto-Archive After 6mo| WARM
        end
        
        subgraph WARM["❄️ Warm Tier (6-18 months)"]
            direction LR
            W_ARCH[Archived Photos<br/>employee_photos/archive/2025/]
            W_ARCH -.->|Auto-Move After 18mo| COLD
        end
        
        subgraph COLD["🧊 Cold Tier (18+ months)"]
            direction LR
            C_HIST[Historical Photos<br/>employee_photos/archive/2024/]
            C_HIST -.->|Delete After 7 years| DEL[🗑️ Deletion]
        end
        
        subgraph META["📊 Metadata Registry (Delta)"]
            direction TB
            T_REG[employee_photo_registry<br/>-------------<br/>🔑 photo_id PK<br/>🆔 employee_id<br/>🔗 photo_url<br/>🔗 thumbnail_url<br/>📏 file_size_bytes<br/>📐 width/height<br/>📅 upload_timestamp<br/>🏷️ classification<br/>✅ is_active<br/>🔄 version<br/>📍 storage_tier]
            
            T_REG -->|Partition By| PART[📁 upload_timestamp<br/>🔍 ZORDER employee_id]
        end
        
        subgraph CONTENT["📄 Content Table (Delta)"]
            direction TB
            T_CONT[workbook_employee_content<br/>-------------<br/>🆔 employee_id<br/>👤 full_name<br/>💼 job_title<br/>🏢 department<br/>📧 email<br/>🖼️ photo_html<br/>🔗 photo_url<br/>📦 metadata_json]
            
            T_CONT -->|Optimized For| OPT[📊 Workbook Queries<br/>🤖 Agent Retrieval]
        end
    end
    
    subgraph "Storage Metrics"
        direction LR
        COST[💰 Cost per GB/month<br/>Hot: $0.023<br/>Warm: $0.015<br/>Cold: $0.008]
        
        PERF[⚡ Access Latency<br/>Hot: <50ms<br/>Warm: <200ms<br/>Cold: <5s]
        
        CAP[📊 Capacity Planning<br/>Current: 2.5 GB<br/>1 Year: 7.5 GB<br/>3 Years: 25 GB<br/>5 Years: 50 GB]
    end
    
    H_CURR -.->|Reference| T_REG
    H_PREV -.->|Reference| T_REG
    W_ARCH -.->|Reference| T_REG
    C_HIST -.->|Reference| T_REG
    T_REG -->|JOIN| T_CONT
    
    style HOT fill:#ff6b6b,color:#fff
    style WARM fill:#ffa502,color:#000
    style COLD fill:#4834df,color:#fff
    style META fill:#50E6FF,color:#000
    style CONTENT fill:#7FBA00,color:#fff
```

---

## 4. Flujo de Consumo por Workbooks

```mermaid
sequenceDiagram
    participant USER as Usuario Final
    participant WB as Fabric Workbook
    participant AUTH as Entra ID
    participant RLS as Row-Level Security
    participant CT as Content Table
    participant REG as Photo Registry
    participant CDN as Azure CDN (Optional)
    participant FILES as OneLake Files
    participant AUD as Audit Log
    
    USER->>WB: Abrir Workbook
    WB->>AUTH: Solicitar Autenticación
    AUTH-->>WB: Devolver Token + Claims
    
    WB->>CT: SELECT * FROM workbook_employee_content<br/>WHERE department IN (user.departments)
    CT->>RLS: Aplicar Filtros de Seguridad
    RLS-->>CT: Registros Filtrados
    
    CT->>REG: JOIN para obtener URLs actualizadas
    REG-->>CT: photo_url + thumbnail_url
    
    CT-->>WB: Resultado con HTML Embeds
    
    WB->>AUD: Log Access Event
    AUD-->>WB: ✅ Logged
    
    loop Para cada imagen en pantalla
        alt CDN Habilitado
            WB->>CDN: GET image (lazy load)
            CDN->>FILES: Fetch if not cached
            FILES-->>CDN: Image Bytes
            CDN-->>WB: Cached Image
        else Sin CDN
            WB->>FILES: GET OneLake URL (SAS)
            FILES-->>WB: Image Bytes
        end
    end
    
    WB-->>USER: Renderizar Dashboard con Fotos
    
    Note over USER,AUD: Lazy Loading + Progressive Rendering<br/>Solo carga imágenes visibles
```

---

## 5. Flujo de Consumo por Agentes IA

```mermaid
sequenceDiagram
    participant USER as Usuario
    participant CHAT as Chat Interface
    participant AGENT as Fabric Data Agent
    participant API as FabricImageAgentAPI
    participant CACHE as Redis Cache
    participant CT as Content Table
    participant REG as Photo Registry
    participant FILES as OneLake Files
    participant AUD as Audit Log
    participant LLM as Azure OpenAI
    
    USER->>CHAT: "Muéstrame información de Gerardo"
    CHAT->>AGENT: User Query
    
    AGENT->>LLM: Procesar Intención
    LLM-->>AGENT: Intención: buscar_empleado(nombre="Gerardo")
    
    AGENT->>API: search_employees_with_photos("Gerardo")
    API->>CACHE: GET cache_key="search:gerardo"
    
    alt Cache Hit
        CACHE-->>API: Cached Results
    else Cache Miss
        CACHE-->>API: NULL
        API->>CT: SELECT * WHERE full_name LIKE '%Gerardo%'
        CT->>REG: JOIN ON employee_id
        REG-->>CT: photo_url + metadata
        CT-->>API: Query Results
        API->>CACHE: SET cache_key="search:gerardo" TTL=3600
    end
    
    API-->>AGENT: Datos Empleado + photo_url
    
    AGENT->>AUD: Log Access (employee_id, agent_id, timestamp)
    AUD-->>AGENT: ✅ Logged
    
    AGENT->>LLM: Generar Respuesta con Context
    LLM-->>AGENT: Response Template
    
    AGENT->>AGENT: Renderizar HTML con Foto
    Note over AGENT: Template:<br/>"Aquí está la información de {nombre}:<br/><img src='{photo_url}' />"
    
    AGENT-->>CHAT: HTML Response
    CHAT->>FILES: GET photo_url (cuando se renderiza)
    FILES-->>CHAT: Image Bytes
    CHAT-->>USER: Mostrar Información + Foto
    
    Note over USER,LLM: Total Latency Target: <2s<br/>Breakdown:<br/>- LLM: ~800ms<br/>- DB Query: ~150ms<br/>- Image Load: ~200ms<br/>- Network: ~100ms
```

---

## 6. Arquitectura de Seguridad y Governance

```mermaid
graph TB
    subgraph "Identity & Access Management"
        direction TB
        ENTRA[Microsoft Entra ID<br/>👤 Users<br/>🤖 Service Principals<br/>🔑 Managed Identities]
        
        ROLES[RBAC Roles<br/>---------<br/>🔴 Fabric Admin<br/>🟡 HR Manager<br/>🟢 HR Viewer<br/>🔵 AI Agent Service]
    end
    
    subgraph "Data Access Control"
        direction TB
        
        subgraph RLS_LAYER[Row-Level Security]
            RLS_FUNC[fn_employee_security<br/>-------------<br/>FILTER BY:<br/>• Department<br/>• Manager Hierarchy<br/>• Self-Service]
            
            RLS_POLICY[Security Policy<br/>Applied to:<br/>• employee_photo_registry<br/>• workbook_employee_content]
        end
        
        subgraph ABAC_LAYER[Attribute-Based Access]
            ABAC_RULES[Access Rules<br/>-------------<br/>IF classification = 'PII'<br/>  REQUIRE role IN ('HR_Admin')<br/>IF access_level = 'L3'<br/>  REQUIRE clearance >= 3]
            
            ABAC_ATTRS[Data Attributes<br/>• classification<br/>• access_level<br/>• allowed_roles]
        end
        
        subgraph MASKING[Dynamic Data Masking]
            MASK_RULES[Masking Logic<br/>-------------<br/>IF NOT IS_MEMBER('HR_Admin')<br/>  RETURN placeholder_image<br/>ELSE<br/>  RETURN photo_url]
        end
    end
    
    subgraph "Audit & Compliance"
        direction TB
        
        AUDIT_TABLE[photo_access_audit<br/>-------------<br/>📝 audit_id<br/>🆔 employee_id<br/>👤 accessed_by<br/>⏰ access_timestamp<br/>📊 access_type<br/>✅ success<br/>❌ denial_reason]
        
        PURVIEW_CAT[Microsoft Purview<br/>Data Catalog<br/>-------------<br/>📁 Asset Registration<br/>🏷️ Auto-Classification<br/>🔍 Lineage Tracking<br/>📜 Compliance Reports]
        
        RETENTION[Retention Policies<br/>-------------<br/>Active Photos: 7 years<br/>Audit Logs: 10 years<br/>Inactive Employees: 2 years]
    end
    
    subgraph "Encryption & Secrets"
        direction TB
        
        ENCRYPT[Encryption<br/>-------------<br/>🔐 At Rest: AES-256<br/>🔐 In Transit: TLS 1.3<br/>🔐 Key Management: Azure Key Vault]
        
        KV[Azure Key Vault<br/>-------------<br/>🔑 SF API Keys<br/>🔑 Database Credentials<br/>🔑 SAS Token Secrets<br/>🔄 Auto-Rotation Enabled]
    end
    
    subgraph "Compliance Standards"
        direction LR
        GDPR[GDPR<br/>✅ Right to Access<br/>✅ Right to Erasure<br/>✅ Data Portability]
        
        SOC2[SOC 2 Type II<br/>✅ Access Controls<br/>✅ Audit Logging<br/>✅ Encryption]
        
        ISO[ISO 27001<br/>✅ Information Security<br/>✅ Risk Management<br/>✅ Incident Response]
    end
    
    %% Relaciones
    ENTRA --> ROLES
    ROLES -.->|Enforce| RLS_LAYER
    ROLES -.->|Enforce| ABAC_LAYER
    
    RLS_FUNC --> RLS_POLICY
    ABAC_RULES --> ABAC_ATTRS
    
    RLS_POLICY -.->|Apply| MASK_RULES
    ABAC_ATTRS -.->|Apply| MASK_RULES
    
    MASK_RULES -.->|Log| AUDIT_TABLE
    AUDIT_TABLE --> PURVIEW_CAT
    PURVIEW_CAT --> RETENTION
    
    KV -.->|Secure| ENTRA
    ENCRYPT -.->|Protect| AUDIT_TABLE
    
    PURVIEW_CAT -.->|Compliance| GDPR
    PURVIEW_CAT -.->|Compliance| SOC2
    PURVIEW_CAT -.->|Compliance| ISO
    
    style ENTRA fill:#FFB900,color:#000,stroke:#d39300,stroke-width:3px
    style RLS_LAYER fill:#7FBA00,color:#fff,stroke:#5e8700,stroke-width:2px
    style ABAC_LAYER fill:#0078D4,color:#fff,stroke:#005a9e,stroke-width:2px
    style AUDIT_TABLE fill:#50E6FF,color:#000,stroke:#00b7c3,stroke-width:2px
    style PURVIEW_CAT fill:#FFB900,color:#000,stroke:#d39300,stroke-width:3px
    style KV fill:#E81123,color:#fff,stroke:#c50f1f,stroke-width:2px
```

---

## 7. Alta Disponibilidad y Disaster Recovery

```mermaid
graph TB
    subgraph "Primary Region: East US"
        direction TB
        
        subgraph PRIMARY[Primary Fabric Workspace]
            P_LH[Lakehouse Primary<br/>📁 Files + Tables]
            P_NB[Pipeline Notebooks]
            P_WB[Workbooks]
        end
        
        P_ONELAKE[OneLake Storage<br/>East US<br/>🔄 Auto-Backup<br/>📸 Point-in-Time Recovery]
    end
    
    subgraph "Secondary Region: West US 2"
        direction TB
        
        subgraph SECONDARY[Secondary Fabric Workspace]
            S_LH[Lakehouse Secondary<br/>📁 Files + Tables<br/>🔄 Read-Replica]
            S_WB[Workbooks Read-Only]
        end
        
        S_ONELAKE[OneLake Storage<br/>West US 2<br/>📋 Geo-Replicated]
    end
    
    subgraph "Global Distribution"
        direction LR
        
        CDN[Azure CDN<br/>🌍 Global Edge Locations<br/>⚡ Cache TTL: 24h]
        
        FRONTDOOR[Azure Front Door<br/>🔀 Traffic Manager<br/>🏥 Health Probes<br/>🔄 Auto-Failover]
    end
    
    subgraph "Backup & Recovery"
        direction TB
        
        BACKUP[Backup Strategy<br/>-------------<br/>🔄 Continuous: Delta Lake<br/>📅 Daily: Full Snapshot<br/>📅 Weekly: Archive]
        
        RTO[Recovery Objectives<br/>-------------<br/>⏱️ RTO: 4 hours<br/>💾 RPO: 15 minutes<br/>📊 Data Loss: <0.1%]
        
        DR_PROC[DR Procedures<br/>-------------<br/>1️⃣ Detect Outage<br/>2️⃣ Validate Secondary<br/>3️⃣ DNS Failover<br/>4️⃣ Monitor Recovery<br/>5️⃣ Post-Mortem]
    end
    
    subgraph "Health Monitoring"
        direction TB
        
        HEALTH[Health Checks<br/>-------------<br/>✅ Storage Availability<br/>✅ API Responsiveness<br/>✅ Query Performance<br/>✅ Pipeline Status]
        
        ALERTS[Alert Configuration<br/>-------------<br/>🔴 P1: Primary Down<br/>🟡 P2: Performance Degraded<br/>🟢 P3: Scheduled Maintenance]
    end
    
    %% Relaciones de Replicación
    P_LH -->|Geo-Replication| S_LH
    P_ONELAKE <-->|Continuous Sync| S_ONELAKE
    P_NB -.->|Git Sync| S_LH
    
    %% Distribución Global
    P_ONELAKE --> CDN
    S_ONELAKE --> CDN
    
    FRONTDOOR -->|Primary Route| PRIMARY
    FRONTDOOR -.->|Failover Route| SECONDARY
    
    %% Backup
    P_ONELAKE --> BACKUP
    BACKUP --> RTO
    
    %% Monitoreo
    PRIMARY --> HEALTH
    SECONDARY --> HEALTH
    HEALTH --> ALERTS
    ALERTS -.->|Trigger| DR_PROC
    
    style PRIMARY fill:#7FBA00,color:#fff,stroke:#5e8700,stroke-width:3px
    style SECONDARY fill:#50E6FF,color:#000,stroke:#00b7c3,stroke-width:3px
    style CDN fill:#E81123,color:#fff,stroke:#c50f1f,stroke-width:2px
    style FRONTDOOR fill:#0078D4,color:#fff,stroke:#005a9e,stroke-width:3px
    style BACKUP fill:#FFB900,color:#000,stroke:#d39300,stroke-width:2px
```

---

## 8. Flujo de Datos con Optimización

```mermaid
graph LR
    subgraph "Request Layer"
        USER[👤 Usuario/Agente]
    end
    
    subgraph "Caching Layer"
        direction TB
        L1[L1 Cache<br/>Browser/Client<br/>⏱️ 5 min]
        L2[L2 Cache<br/>Azure CDN<br/>⏱️ 24 hours]
        L3[L3 Cache<br/>Redis<br/>⏱️ 1 hour]
    end
    
    subgraph "API Gateway"
        AGW[Azure API Management<br/>🔐 Auth<br/>⏱️ Rate Limiting<br/>📊 Analytics]
    end
    
    subgraph "Application Layer"
        direction TB
        API[FabricImageAgentAPI<br/>🔌 REST Endpoints]
        BL[Business Logic<br/>🔍 Query Optimization<br/>🔄 Batch Processing]
    end
    
    subgraph "Data Layer - Optimized"
        direction TB
        
        MAT_VIEW[Materialized View<br/>workbook_employee_content<br/>🔄 Refresh: Every 15 min<br/>📊 Pre-aggregated]
        
        HOT_PART[Hot Partition<br/>employee_photo_registry<br/>📅 Recent 6 months<br/>🔍 ZORDER: employee_id<br/>⚡ Auto-Optimize ON]
        
        COLD_PART[Cold Partition<br/>employee_photo_registry<br/>📅 Older data<br/>📦 Compressed]
    end
    
    subgraph "Storage Layer"
        direction LR
        HOT_FILES[Hot Files<br/>SSD-backed<br/>⚡ <50ms]
        
        WARM_FILES[Warm Files<br/>Standard<br/>⚡ <200ms]
    end
    
    %% Flujo de Request
    USER -->|1. Request| L1
    L1 -->|Miss| L2
    L2 -->|Miss| L3
    L3 -->|Miss| AGW
    
    AGW --> API
    API --> BL
    
    BL -->|Query Metadata| MAT_VIEW
    MAT_VIEW -->|Recent Data| HOT_PART
    MAT_VIEW -->|Historical| COLD_PART
    
    BL -->|Fetch Files| HOT_FILES
    BL -->|Fetch Archived| WARM_FILES
    
    %% Flujo de Response
    HOT_FILES -.->|Response| BL
    BL -.->|Cache| L3
    L3 -.->|Response| AGW
    AGW -.->|Cache| L2
    L2 -.->|Response| USER
    
    %% Métricas de Optimización
    subgraph "Performance Metrics"
        direction TB
        METRICS[Targets Achieved<br/>-------------<br/>📊 Cache Hit Rate: >80%<br/>⏱️ P95 Latency: <200ms<br/>💰 Cost Reduction: 70%<br/>🔄 Query Throughput: 10K/min]
    end
    
    L2 -.->|Report| METRICS
    L3 -.->|Report| METRICS
    MAT_VIEW -.->|Report| METRICS
    
    style L1 fill:#E81123,color:#fff
    style L2 fill:#E81123,color:#fff
    style L3 fill:#E81123,color:#fff
    style MAT_VIEW fill:#7FBA00,color:#fff
    style HOT_PART fill:#ff6b6b,color:#fff
    style COLD_PART fill:#4834df,color:#fff
    style METRICS fill:#FFB900,color:#000
```

---

## 📊 Tabla Comparativa de Arquitecturas

| Aspecto | Arquitectura Actual (Base64) | Arquitectura Propuesta (Files) | Mejora |
|---------|------------------------------|--------------------------------|--------|
| **Storage Cost** | $0.18/GB (Delta) | $0.023/GB (Files) | **-87%** 💰 |
| **Query Latency** | 250ms (avg) | 50ms (avg) | **-80%** ⚡ |
| **Scalability** | Limited (2GB max table) | Unlimited | **∞** 📈 |
| **Cache Hit Rate** | N/A | >80% | **New** 🎯 |
| **Geo-Replication** | Manual | Automatic | **100%** 🌍 |
| **Governance** | Basic | Enterprise (Purview) | **+500%** 🔒 |
| **DR/HA** | No | Yes (Multi-region) | **New** 🏥 |
| **API Access** | Direct table query | Optimized API Layer | **+300%** 🔌 |

---

## 🎯 Decisiones Arquitectónicas Clave

### ADR-001: Almacenamiento en Lakehouse Files vs. Delta Embedding

**Decisión:** Utilizar Lakehouse Files para binarios + Delta para metadata

**Contexto:**
- Imágenes ocupan 500KB promedio
- 5,000 empleados actuales, proyección 50,000 en 5 años
- Costos de storage son críticos

**Consecuencias:**
- ✅ Reducción de costos 87%
- ✅ Mejor performance de queries
- ✅ Escalabilidad ilimitada
- ❌ Complejidad adicional de gestión de archivos
- ❌ Requiere lifecycle management manual

---

### ADR-002: Redis Cache Layer

**Decisión:** Implementar Redis como L3 cache para metadata

**Contexto:**
- 80% de queries son para los mismos 100 empleados
- Latencia de query a Delta es ~150ms
- SLA target es <100ms end-to-end

**Consecuencias:**
- ✅ Reducción de latencia 60%
- ✅ Menor carga en Lakehouse
- ✅ Mejor experiencia de usuario
- ❌ Costo adicional Redis (~$200/mes)
- ❌ Cache invalidation complexity

---

### ADR-003: Multi-Region Replication

**Decisión:** Implementar geo-replication para DR

**Contexto:**
- SLA requirement: 99.9% uptime
- RTO: 4 hours, RPO: 15 minutes
- Usuarios distribuidos globalmente

**Consecuencias:**
- ✅ Alta disponibilidad garantizada
- ✅ Mejor latencia para usuarios remotos
- ✅ Compliance con regulaciones
- ❌ Costo adicional storage replication (+30%)
- ❌ Complejidad operacional

---

## 📚 Leyenda de Símbolos

| Símbolo | Significado |
|---------|-------------|
| 📊 | Datos / Tablas |
| 📁 | Archivos / Storage |
| 🔐 | Seguridad / Autenticación |
| ⚡ | Performance / Optimización |
| 🔄 | Sincronización / Replicación |
| 💰 | Costos |
| 📈 | Escalabilidad |
| 🎯 | KPI / Métrica |
| ⚠️ | Alerta / Warning |
| ✅ | Estado OK / Exitoso |
| ❌ | Error / Fallido |
| 🏥 | Alta Disponibilidad |
| 🌍 | Global / Multi-región |

---

*Diagramas generados con Mermaid - Versión 10.9.0*  
*Para editar los diagramas, visite: [Mermaid Live Editor](https://mermaid.live)*
