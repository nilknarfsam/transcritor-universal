# CortexFlow

**Plataforma de preparação inteligente de conhecimento para IA.**

Transforme conteúdos brutos (áudio, vídeo, documentos, OCR) em Markdown e formatos AI-ready para NotebookLM, GPT Projects, RAG, Obsidian e agentes IA.

> Ponto de entrada: `app.py`

---

## UX 3.0.2 — Aba Transcrição

A aba **Transcrição** é a tela principal do CortexFlow (primeira aba ao abrir o app).

### Nova fila premium

* **Toolbar:** Adicionar arquivos, Adicionar pasta, Remover selecionado, Limpar fila
* **Tabela:** Arquivo, Tipo, Status, Progresso, Saída, Tempo
* **Estado vazio:** mensagem + formatos aceitos (áudio, vídeo, PDF, DOCX, XLSX, imagens, TXT)
* **Detalhes** do item selecionado (caminhos, cache HIT/MISS, modo de exportação, tipo de conteúdo)
* **Ações:** Iniciar transcrição (botão principal), Cancelar, Abrir pasta de saída
* **Preview** do resultado como painel secundário (exportar TXT, JSON, MD)
* **Drag and drop** em toda a janela e na fila

Preferências de tema, idioma e biblioteca ficam na aba **Configurações**. Sidebar: marca CortexFlow, versão e slogan.

---

## Recursos

* **Transcrição (Whisper):** MP3, WAV, M4A, FLAC, MP4, AVI, MOV, MKV
* **Textos:** TXT, PDF, DOCX, XLSX
* **OCR em imagens:** JPG, JPEG, PNG (via Tesseract)
* **Fila:** vários arquivos com status (aguardando, processando, concluído, erro, cancelado)
* **Controles:** iniciar/cancelar fila, barra de progresso geral, contadores por status
* **Saída automática:** mesma pasta do arquivo ou pasta global; botão **Abrir pasta de saída**
* **Idiomas:** detecção automática ou seleção manual (pt, en, es, fr, de, it, ru, zh)
* **UX:** arrastar & soltar, preview inteligente para textos grandes, tema escuro/claro
* **Exportação:** TXT, JSON, Markdown (automática e manual)
* **Histórico:** transcrições e sessões parciais em `data/historico_transcricoes.json`
* **Fila persistente:** estado da fila em `data/queue_state.json` com recovery automático
* **Cache inteligente:** SHA256 + `data/cache_registry.json` para evitar reprocessamento
* **Log técnico:** `data/logs/app.log` (erros e eventos da fila)
* **Design System:** tokens visuais premium em `src/ui/design/`
* **Pipeline AI-ready:** modos Raw, Clean, AI Ready e NotebookLM
* **Semantic Intelligence:** referências, highlights, tópicos, índice e chunking
* **Knowledge Library:** workspaces, coleções, catálogo e busca local na aba **Biblioteca**
* **Study Intelligence:** flashcards, quizzes, revisão rápida e notas (modo `study_mode`)
* **Knowledge Dataset Engine:** datasets por documento, chunks indexados e índices globais (aba **Datasets**)
* **Knowledge Graph:** busca semântica local, documentos relacionados e navegação por tópicos (aba **Grafo / Conexões**)
* **Premium Workspace:** busca unificada, cards de resultado, detalhe de documento e dashboard (aba **Conhecimento**)

---

## Estrutura do projeto

```
app.py
src/
  semantic/                    # Semantic Intelligence Engine
    references/
    highlights/
    indexing/
    timestamps/
    topics/
  ai_ready/                    # Pipeline AI-ready
    metadata/                  # YAML frontmatter
    templates/                 # Sermão, podcast, aula, genérico
    formatters/                # Markdown beautifier
    chunking/                  # Fundação RAG
    exporters/                 # NotebookLM exporter
    pipeline.py
    stages.py
  cache/                       # Cache Intelligence Engine
    hash_manager.py
    cache_engine.py
    cache_registry.py
  library/                     # Knowledge Library Engine
    collections/
    workspaces/
    catalog/
    search/
    metadata/
    library_engine.py
  study/                       # Study Intelligence Engine
    flashcards/
    quizzes/
    summaries/
    revisions/
    difficulty/
    notes/
    study_engine.py
  datasets/                    # Knowledge Dataset Engine
    registry/
    builders/
    exporters/
    validators/
    statistics/
    dataset_engine.py
  knowledge/                   # Dashboard e métricas agregadas
  knowledge_graph/             # Grafo de conhecimento e busca semântica
    nodes/
    edges/
    search/
    navigation/
    exporters/
    graph_engine.py
  core/
    transcription_service.py   # Whisper (singleton)
    extraction_service.py      # TXT, PDF, DOCX, XLSX, OCR
    export_service.py
    queue_manager.py
    persistent_queue.py        # Fila persistente
    performance_metrics.py     # Métricas de pipeline
    settings_service.py
    log_service.py
    job_errors.py
  models/
    transcription_job.py
  ui/
    design/                    # Design System CortexFlow
      colors.py
      fonts.py
      spacing.py
      theme_manager.py
    main_window.py
    queue_panel.py
    library_panel.py
    graph_panel.py
    knowledge_workspace_panel.py
    document_detail_panel.py
    components/knowledge_widgets.py
    study_panel.py
    settings_panel.py
    result_panel.py
data/
  library/
    collections.json
    workspaces.json
    catalog.json
  settings.json
  historico_transcricoes.json
  queue_state.json
  cache_registry.json
  cache/
  knowledge_graph/
    graph.json
    graph_export.md
    knowledge_report.md
  logs/app.log
```

---

## Requisitos (Windows)

### 1) Python 3.10+

* Baixe e instale o Python (marque **“Add Python to PATH”**).
* [https://www.python.org/downloads/](https://www.python.org/downloads/)

### 2) FFmpeg (para Whisper)

* Adicione o diretório `bin` do FFmpeg ao PATH.
* [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
* Builds Windows: [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)

### 3) Tesseract OCR (para imagens)

* Instale com os idiomas desejados (ex.: Portuguese).
* [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)

> Ex.: adicione `C:\Program Files\Tesseract-OCR\` ao PATH.

### 4) Dependências Python

```bash
pip install -r requirements.txt
```

Ou execute `instalar_dependencias.bat`.

---

## Como executar

Na pasta do projeto:

```bash
python app.py
```

Compatível com o comando legado:

```bash
python app_transcricao.py
```

---

## Como usar

1. Abra o app e ajuste **tema**, **idioma** e **formato padrão** no painel esquerdo.
2. **Adicione arquivos** (botão ou drag & drop) — entram na fila de processamento.
3. Opcional: defina uma **pasta global de saída** ou deixe na mesma pasta do arquivo.
4. Clique em **Iniciar Fila** para processar todos os itens aguardando.
5. Use **Cancelar Fila** para interromper após o item atual; o progresso parcial fica no histórico.
6. Acompanhe **contadores** e a **barra de progresso** acima da lista.
7. Selecione um item para ver o resultado (preview truncado em textos grandes; use **Carregar texto completo**).
8. **Abrir pasta de saída** abre o Explorer na pasta do item selecionado ou na pasta global.
9. Consulte o histórico no painel de configurações; detalhes técnicos em `data/logs/app.log`.

---

## Atalhos

* **Ctrl + O** → Adicionar arquivos
* **Ctrl + T** → Iniciar fila
* **Ctrl + E** → Exportar (diálogo de formato)
* **Ctrl + Q** → Fechar app

---

## Formatos suportados

* **Áudio:** `.mp3`, `.wav`, `.m4a`, `.flac`
* **Vídeo:** `.mp4`, `.avi`, `.mov`, `.mkv`
* **Texto:** `.txt`, `.pdf`, `.docx`, `.xlsx`
* **Imagem (OCR):** `.jpg`, `.jpeg`, `.png`

---

## Configuração PATH no Windows

### FFmpeg

```bash
ffmpeg -version
```

### Tesseract

```bash
tesseract --version
```

Se necessário:

```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

---

## Problemas comuns

* **Whisper não instalado** → `pip install -r requirements.txt`
* **ffmpeg not found** → FFmpeg não está no PATH
* **tesseract not installed** → Tesseract não está no PATH
* **PDF sem texto** → PDF é imagem; use OCR em imagem exportada ou ferramenta dedicada

---

## Using CortexFlow with NotebookLM

O CortexFlow transforma conteúdo bruto em **conhecimento estruturado** pronto para importar no [NotebookLM](https://notebooklm.google.com), GPT Projects, RAG e Obsidian.

### Pipeline de exportação

```
RAW → CLEAN → AI_READY → SEMANTIC → NOTEBOOKLM
```

| Modo | Descrição |
|------|-----------|
| **Raw** | Texto original (comportamento legado) |
| **Clean** | Texto normalizado e embelezado |
| **AI Ready** | Markdown com seções semânticas (resumo, pontos, frases, referências) |
| **NotebookLM** | YAML metadata + markdown estruturado otimizado para IA |

Configure **Modo de exportação** e **Tipo de conteúdo** no painel esquerdo. A escolha é salva em `data/settings.json`.

### Estrutura YAML (frontmatter)

Documentos no modo NotebookLM incluem metadata opcional:

```yaml
---
title: Nome do arquivo
source: /caminho/origem.mp3
language: pt
content_type: sermon
pipeline_stage: notebooklm
topics:
  - fé
tags:
  - evangelho
---
```

Campos ausentes são omitidos automaticamente.

### Templates disponíveis

* **generic** — Resumo, Conteúdo, Pontos, Frases, Referências, Tags
* **sermon** — Estrutura da Mensagem, Contexto Bíblico, Aplicações, Referências Bíblicas
* **podcast** — Timestamps, Pontos principais
* **course** — Exercícios e reflexões para aulas

### Dica de uso

1. Selecione modo **NotebookLM** e formato **md**.
2. Escolha o template adequado (ex.: `sermon` para pregações).
3. Processe a fila e importe o `.md` gerado no NotebookLM.

Todo o processamento é **local e determinístico** — sem APIs externas.

---

## Semantic Intelligence Engine

A camada semântica do CortexFlow (`src/semantic/`) transforma texto estruturado em **conhecimento navegável** — 100% local, sem APIs externas.

### Capacidades

| Módulo | Função |
|--------|--------|
| **Referências bíblicas** | Detecta João 11:25, Romanos 8:28, Salmos 91, etc. |
| **Highlights** | Extrai frases marcantes por heurísticas de impacto |
| **Tópicos** | Identifica fé, graça, salvação, ressurreição, etc. |
| **Índice automático** | Gera `# Índice` a partir de títulos e timestamps |
| **Timestamps** | Formata `## [00:14:22] Título do segmento` |
| **Chunking semântico** | Prepara blocos RAG-ready com IDs, tópicos e relação pai/filho |

### Pipeline semântico

Ativo automaticamente no modo **NotebookLM**. O preview exibe badge **Semantic Ready** com contagem de referências, highlights, chunks e tópicos detectados.

### Preparação RAG

Cada chunk exporta estrutura:

```json
{
  "chunk_id": "chunk-a1b2c3d4",
  "title": "O chamado de Lázaro",
  "start_timestamp": "00:12:14",
  "topics": ["fé", "ressurreição"],
  "content": "..."
}
```

Embeddings e busca vetorial virão em sprints futuras.

---

## Persistent Knowledge Queue

A fila do CortexFlow persiste automaticamente em `data/queue_state.json`.

### O que é salvo

* Jobs aguardando, processando, concluídos, cancelados e com erro
* Progresso por job e checkpoints do pipeline (Whisper, OCR, clean, semantic, notebooklm)
* Timestamps, modo de exportação e template usados na sessão

### Recovery System

Ao abrir o app:

1. Detecta `queue_state.json` e restaura a fila
2. Jobs em **processando** voltam para **aguardando** (retomada segura)
3. Remove jobs corrompidos (arquivo ausente no disco)
4. Exibe indicador **Queue Restored** na UI
5. Use **Iniciar Fila** para continuar de onde parou

Botão **Restaurar Última Fila** recarrega manualmente o último snapshot.

---

## Cache Intelligence Engine

Cache local e determinístico em `src/cache/` — sem APIs externas.

### SHA256 fingerprint

Cada arquivo recebe hash SHA256 + tamanho. O fluxo é:

```
arquivo → SHA256 → verificar cache → reutilizar resultados
```

### Pipeline com cache

```
RAW → CACHE CHECK → CLEAN → AI_READY → SEMANTIC → NOTEBOOKLM
```

Estágios cacheados: transcrição Whisper, OCR, markdown clean, semantic, export NotebookLM e chunks.

Registro em `data/cache_registry.json` com hash, tamanho, nome, data, export mode, estágio e caminhos gerados.

### UI

* **Cache HIT** / **Cache MISS** / **Cache PARTIAL**
* **Limpar Cache** — remove registry e `data/cache/`
* Contador de itens e tamanho do cache

O histórico registra `cache_hit`, `recovery_used`, `processing_time` e `reused_pipeline`.

---

## Knowledge Library Engine

O CortexFlow organiza conhecimento em **unidades catalogadas**, não apenas arquivos soltos.

### Workspaces

Bibliotecas contextuais separadas (ex.: Instituto Renascer, Engenharia ICT). Cada workspace agrupa coleções e documentos. Configure no painel **Biblioteca** em Configurações.

Persistência: `data/library/workspaces.json`

### Collections

Coleções temáticas: Teologia, Podcasts, Cursos, Reuniões, etc. Todo documento processado pode pertencer a uma coleção e receber tags.

Persistência: `data/library/collections.json`

### Catálogo inteligente

Cada processamento concluído gera entrada em `data/library/catalog.json` com título, hash, workspace, coleção, speaker, autor, tópicos, referências, highlights, chunks, pipeline e caminhos de saída.

### Local Search

Busca textual local (sem embeddings) na aba **Biblioteca**: filtre por workspace e coleção; pesquise título, tópicos, tags e referências; ordene por data ou score semântico.

### Semantic Relationships

`relationship_builder.py` detecta relações entre documentos por tópicos, referências, speaker e coleção compartilhados. O **Knowledge Graph** (`src/knowledge_graph/`) persiste nós e arestas em `data/knowledge_graph/graph.json` para navegação estruturada.

### Metadata expandida (YAML)

Frontmatter NotebookLM inclui: `workspace`, `collection`, `category`, `knowledge_type`, `semantic_score`, `chunk_count`.

### Organização cognitiva

1. Escolha **workspace** e **coleção** antes de processar.
2. Preencha autor, speaker e tags (opcional).
3. Processe na fila — o catálogo atualiza automaticamente.
4. Navegue e pesquise na aba **Biblioteca**; abra o Markdown exportado.

---

## Study Intelligence Engine

Transforma conhecimento organizado em **aprendizado estruturado** — 100% local.

### Study Mode

Novo modo de exportação: **study_mode**. Pipeline:

```
RAW → CACHE CHECK → CLEAN → AI_READY → SEMANTIC → STUDY → NOTEBOOKLM
```

### Flashcards

Gerados a partir de chunks, highlights, tópicos e referências. Estrutura JSON:

```json
{
  "question": "...",
  "answer": "...",
  "topic": "...",
  "difficulty": "básico"
}
```

Arquivo: `{nome}_flashcards.json`

### Quiz Generator

Tipos: múltipla escolha, verdadeiro/falso, perguntas abertas e revisão rápida.

Arquivo: `{nome}_quizzes.json`

### Revisão Inteligente

Seções automáticas no Markdown e em `{nome}_quick_review.md`:

* **Revisão Rápida**
* **Conceitos Principais**
* **Perguntas para Revisão**
* **Aplicações Práticas**
* **Reflexões**

Notas completas: `{nome}_study_notes.md`

### Dificuldade

Classificação **básico**, **intermediário** ou **avançado** (tamanho, densidade, tópicos, referências). Campo `difficulty` no YAML.

### UI

* Aba **Estudo** — preview de flashcards, quizzes e revisão rápida
* Badge **Study Ready** no painel de resultado
* Histórico: `flashcards_count`, `quizzes_count`, `difficulty`, `study_exports`

---

## Semantic Search

Busca contextual **local e determinística** sobre o grafo de conhecimento — sem embeddings e sem APIs externas.

### O que é pesquisado

* Título e metadados de documentos
* Tópicos, tags, speaker e autor
* Referências bíblicas e highlights
* Chunks RAG-ready
* Flashcards e quizzes (quando exportados em `study_mode`)
* Coleções e workspaces

### Como usar

1. Aba **Biblioteca** — campo **Busca semântica** e botão **Ver relacionados** no documento selecionado.
2. Aba **Grafo / Conexões** — busca completa com motivos de conexão e exploração por tópico.
3. Resultados mostram score simples e razões (`shared_topics`, `shared_references`, `similar_chunks`, etc.).

Persistência do índice: `data/knowledge_graph/graph.json` (rebuild automático após cada documento catalogado).

---

## Knowledge Graph Foundation

O CortexFlow conecta conteúdos em um grafo navegável preparado para RAG futuro.

### Tipos de nós

`document`, `topic`, `tag`, `speaker`, `author`, `collection`, `workspace`, `bible_reference`, `chunk`, `flashcard`, `quiz`

### Tipos de relações

`belongs_to_workspace`, `belongs_to_collection`, `has_topic`, `has_tag`, `has_reference`, `has_chunk`, `has_flashcard`, `has_quiz`, `related_by_topic`, `related_by_reference`, `related_by_speaker`, `related_by_collection`

### Rebuild seguro

O grafo é reconstruído a partir de:

* `data/library/catalog.json`
* `data/library/collections.json` e `workspaces.json`
* Sidecars de estudo (`*_flashcards.json`, `*_quizzes.json`)
* Histórico enriquecido (`catalog_id`, contagens de estudo)

Botão **Reconstruir grafo** na aba **Grafo / Conexões** força sincronização manual.

---

## Related Documents

Dado um `catalog_id`, o sistema lista documentos relacionados com score e motivos:

```json
{
  "document_id": "doc-abc123",
  "score": 3.6,
  "reasons": ["shared_topics", "shared_references"]
}
```

Critérios: tópicos e referências compartilhados, mesmo speaker/autor, mesma coleção, similaridade lexical entre chunks.

---

## Topic Navigation

Informe um tópico (ex.: `ressurreição`) na aba **Grafo / Conexões** para listar:

* Documentos catalogados
* Chunks com esse tópico
* Flashcards e quizzes vinculados
* Referências bíblicas associadas
* Coleções conectadas

---

## Graph Export

Exportação Markdown em `data/knowledge_graph/graph_export.md` com:

* Visão geral do grafo (nós, arestas, documentos conectados)
* Tópicos mais conectados
* Referências mais usadas
* Coleções e documentos relacionados

Botão **Exportar MD** na aba **Grafo / Conexões**.

O histórico registra `graph_node_id`, `related_documents_count`, `semantic_search_hits` e `graph_updated_at`.

### Preparação para embeddings e RAG

O grafo reutiliza chunks semânticos já exportados pelo pipeline. Embeddings e busca vetorial serão camadas futuras sobre esta fundação — sem alterar o catálogo nem o fluxo atual.

---

## Premium Knowledge Workspace

A aba **Conhecimento** é o hub central para navegar tudo que já foi processado.

### Fluxo natural

1. Processe arquivos na aba **Transcrição**.
2. O catálogo e o grafo atualizam automaticamente.
3. Abra **Conhecimento** e use a **busca unificada**.
4. Selecione um card de resultado.
5. Veja o **detalhe do documento** à direita.
6. Abra o Markdown, exporte um resumo ou veja **relacionados** no grafo.

### Unified Search

Busca em uma única interface:

* Documentos, tópicos, tags, chunks, highlights
* Flashcards, quizzes, referências, speakers, autores
* Coleções e workspaces

**Filtros:** workspace, coleção, tipo de nó, template, modo de exportação, dificuldade.

Preferências salvas em `data/settings.json` (`ui_last_search_query`, filtros `ui_search_filter_*`, `ui_last_tab`).

---

## Document Details

O painel de detalhe exibe:

* Caminho exportado, workspace, coleção, tags, tópicos
* Referências, highlights, chunks, flashcards e quizzes
* Documentos relacionados com score e motivos

**Ações:** abrir Markdown, abrir pasta, copiar caminho, exportar resumo (`*_knowledge_summary.md`).

Na **Biblioteca**, use **No Workspace** para abrir o documento selecionado diretamente na aba Conhecimento.

---

## Knowledge Dashboard

Faixa de métricas no topo do workspace:

* Documentos, datasets, readiness médio, chunks, flashcards, quizzes, tópicos, relações
* Cache hits e tempo médio de processamento (histórico)

Dados agregados de catálogo, grafo, datasets e cache local.

---

## Knowledge Dataset Engine

O CortexFlow produz **datasets de conhecimento** prontos para qualquer IA — localmente, sem embeddings nem APIs externas.

### Pipeline

```
RAW → CACHE CHECK → CLEAN → AI_READY → SEMANTIC → STUDY → NOTEBOOKLM → DATASET
```

Após cada processamento em modo `ai_ready`, `notebooklm` ou `study_mode`, o estágio **DATASET**:

* Gera um **knowledge dataset** por documento (tópicos, referências, chunks, flashcards, quizzes, metadados)
* Gera **chunk datasets** independentes por bloco semântico
* Reconstrói **índices globais** (tópicos, referências, autores, speakers, coleções, workspaces)
* Atualiza catálogo e grafo (fluxo existente) e persiste em `data/datasets/`

### Artefatos (`data/datasets/`)

| Arquivo | Conteúdo |
|---------|----------|
| `knowledge_datasets.json` | Datasets completos por documento |
| `chunk_datasets.json` | Registros por chunk |
| `knowledge_index.json` | Índices globais |
| `dataset_statistics.json` | Métricas agregadas |
| `dataset_validation_report.json` | Relatório de validação |

Cada registro inclui `created_at`, `updated_at`, `source_document` e `dataset_version`.

---

## Dataset Explorer

Aba **Datasets** no app:

* Lista datasets gerados com documento associado, chunks, versão e estatísticas
* **Abrir pasta** `data/datasets/`
* **Exportar dataset** (cópia JSON)
* **Validar datasets** (campos obrigatórios, IDs únicos, integridade de chunks e referências)

---

## Dataset Validation

O validador (`DatasetValidator`) verifica:

* Campos obrigatórios em knowledge e chunk datasets
* IDs únicos (`dataset_id`, `chunk_id`)
* Integridade de chunks referenciados
* Integridade de referências e índices

O relatório é salvo em `dataset_validation_report.json`.

---

## Knowledge Readiness Score

Pontuação **0–100** (`knowledge_readiness_score`) por documento, com base em:

* Metadados e título
* Chunks semânticos
* Tópicos e referências
* Flashcards e quizzes (modo study)
* Workspace, coleção, autor/speaker e highlights

Exibido no **Dataset Explorer** e no **Knowledge Dashboard** (card Readiness).

---

## Preparação para RAG

Os datasets e índices são a camada de dados **determinística** antes de vetorização futura:

* **Chunks** com `chunk_id`, tópicos e conteúdo — prontos para embedding offline posterior
* **Índices invertidos** por tópico, referência, autor e coleção — navegação e filtros sem vector DB
* **NotebookLM / GPT Projects:** export Markdown + JSON estruturado lado a lado
* **Knowledge Graphs:** IDs estáveis ligando documentos, chunks e materiais de estudo

Nenhum embedding, vector database ou API externa é usado nesta versão — o foco é **produzir dados perfeitos para IA**.

---

## Knowledge Report

Exportação Markdown em `data/knowledge_graph/knowledge_report.md`:

* Visão geral, workspaces e coleções
* Tópicos mais frequentes e documentos mais conectados
* Estatísticas e recomendações de organização

Botão **Relatório** na aba **Grafo / Conexões**.

---

## Posicionamento

CortexFlow não é apenas um transcritor. É uma **plataforma de ingestão, estruturação e preparação de conhecimento para IA**.

---

## Changelog

Veja [CHANGELOG.md](CHANGELOG.md).
