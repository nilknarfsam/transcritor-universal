# Changelog

## [3.0.2] - 2026-05-28

### UX 3.0.2 — Aba Transcrição

- **Nova fila premium** na aba **Transcrição**: toolbar (arquivos, pasta, remover, limpar), tabela com colunas Arquivo, Tipo, Status, Progresso, Saída e Tempo.
- **Estado vazio** com mensagem orientativa e formatos aceitos (áudio, vídeo, PDF, DOCX, XLSX, imagens, TXT).
- **Painel de detalhes** do item selecionado (caminhos, status, cache, tempo, modo e template).
- **Badges padronizados** para aguardando, processando, concluído, erro, cancelado, cache hit e cache miss.
- **Ações principais:** Iniciar transcrição (destaque), Cancelar e Abrir pasta de saída; proporção 7:3 entre fila e preview.
- **Adicionar pasta** via diálogo (arquivos suportados recursivos) sem alterar `QueueManager`.
- Funções secundárias preservadas: restaurar fila, limpar cache, drag and drop, exportações do preview.

## [2.9.0] - 2026-05-28

### Added

- **Premium Knowledge Workspace** — aba **Conhecimento** com busca unificada e dashboard.
- **Unified Search Engine** — catálogo + grafo com filtros (workspace, coleção, tipo, template, modo, dificuldade).
- **Search Result Cards** — cards com score, motivo, tópicos e ações rápidas.
- **Document Detail Panel** — detalhe completo, relacionados e export de resumo.
- **Knowledge Dashboard** — métricas agregadas (docs, chunks, flashcards, cache, tempo médio).
- **Knowledge Report** — `data/knowledge_graph/knowledge_report.md`.
- Componentes UI reutilizáveis em `src/ui/components/knowledge_widgets.py`.
- Persistência de navegação: `ui_last_tab`, `ui_last_search_query`, filtros `ui_search_filter_*`.

### Changed

- Aba **Grafo / Conexões** — cards de tópicos, filtro por relação, UI refinada.
- **Biblioteca** — botão **No Workspace**; integração com fluxo Conhecimento.
- Versão da UI **2.9**.

## [2.8.0] - 2026-05-28

### Added

- **Knowledge Graph Foundation** em `src/knowledge_graph/` (nós, arestas, registry).
- **Semantic Search** — busca contextual local sem embeddings.
- **Related Documents** e **Topic Navigation** com scores e motivos de conexão.
- **Graph Stats** e exportação `data/knowledge_graph/graph_export.md`.
- Persistência `data/knowledge_graph/graph.json` com rebuild a partir do catálogo.
- Aba **Grafo / Conexões**; busca semântica e **Ver relacionados** na Biblioteca.
- Histórico: `graph_node_id`, `related_documents_count`, `semantic_search_hits`, `graph_updated_at`.

### Changed

- Versão da UI **2.8**; README com seções de grafo e busca semântica.
- `KnowledgeLibrary` atualiza o grafo após catalogar documentos.

## [2.7.0] - 2026-05-28

### Added

- **Study Intelligence Engine** em `src/study/`.
- **Flashcard Generator** — chunks, highlights, tópicos e referências.
- **Quiz Generator** — múltipla escolha, V/F, abertas e revisão rápida.
- **Study Summary** — revisão rápida, conceitos e pontos importantes.
- **Difficulty Engine** — básico / intermediário / avançado no YAML.
- **Study Notes** — aplicações, reflexões e perguntas para revisão.
- Modo **study_mode** e estágio **STUDY** no pipeline.
- Exportações: `*_flashcards.json`, `*_quizzes.json`, `*_study_notes.md`, `*_quick_review.md`.
- Aba **Estudo** e badge **Study Ready** na UI.

### Changed

- Pipeline: `SEMANTIC → STUDY → NOTEBOOKLM` quando `study_mode` está ativo.
- Histórico enriquecido com métricas educacionais.

## [2.6.0] - 2026-05-28

### Added

- **Knowledge Library Engine** em `src/library/` (workspaces, collections, catalog, search).
- **Collection System** — coleções temáticas em `data/library/collections.json`.
- **Workspace System** — bibliotecas contextuais em `data/library/workspaces.json`.
- **Knowledge Catalog** — catálogo de documentos em `data/library/catalog.json`.
- **Library Search** — busca textual local com filtros e ordenação.
- **Semantic Relationships** — relações por tópicos, referências, speaker e coleção.
- **Knowledge Stats** na UI da aba Biblioteca.
- Aba **Biblioteca** com filtros, busca e abrir Markdown exportado.
- Metadata YAML expandida: workspace, collection, category, knowledge_type, semantic_score, chunk_count.
- Histórico: workspace, collection, catalog_id, semantic_relationships.

### Changed

- `QueueManager` cataloga automaticamente documentos concluídos.
- `ExportContext` e painel de configurações incluem contexto de biblioteca.

## [2.5.0] - 2026-05-28

### Added

- **Persistent Knowledge Queue** — `persistent_queue.py` e `data/queue_state.json`.
- **Queue Recovery** automático ao iniciar o app; botão **Restaurar Última Fila**.
- **Auto-save incremental** de checkpoints (Whisper, OCR, semantic, notebooklm).
- **Cache Intelligence Engine** em `src/cache/` (SHA256, registry, engine).
- **Cache de pipeline** — whisper, OCR, clean, semantic, notebooklm, chunks.
- **Performance metrics** — tempos Whisper, OCR, semantic e total no histórico.
- UI: indicadores Cache HIT/MISS, Queue Restored, **Limpar Cache**, estatísticas de cache.

### Changed

- `QueueManager` integra persistência, cache e métricas sem alterar drag & drop ou exportações.
- Histórico enriquecido: `cache_hit`, `recovery_used`, `processing_time`, `reused_pipeline`.

## [2.4.0] - 2026-05-28

### Added

- **Semantic Intelligence Engine** em `src/semantic/`.
- **Detector de referências bíblicas** com livro, capítulo, versículo e referência completa.
- **Highlight Engine** — frases marcantes por heurísticas locais.
- **Índice automático** baseado em títulos, timestamps e blocos semânticos.
- **Timestamp Intelligence** — parser, normalizador e formatter Markdown.
- **Topic Extractor** — tópicos e tags automáticos na metadata YAML.
- **Chunking semântico avançado** com IDs únicos, relação pai/filho e metadata RAG-ready.
- Pipeline **RAW → CLEAN → AI_READY → SEMANTIC → NOTEBOOKLM**.
- Preview UI com badge **Semantic Ready** e contadores semânticos.
- Histórico enriquecido: referências, highlights, chunks e tópicos detectados.

### Changed

- `NotebookLMExporter` integra camada semântica antes da exportação final.
- `TranscriptionJob` armazena `semantic_metadata` por item processado.

## [2.3.0] - 2026-05-28

### Added

- **Pipeline NotebookLM-ready:** RAW → CLEAN → AI_READY → NOTEBOOKLM.
- **Metadata YAML** padronizada em `src/ai_ready/metadata/`.
- **Templates semânticos:** generic, sermon, podcast, course.
- **Markdown formatter** determinístico (normalize, beautify, semantic paragraphs).
- **Chunking foundation** para RAG futuro (tamanho, headers, timestamps, semântico).
- **Modos de exportação:** raw, clean, ai_ready, notebooklm (UI + `settings.json`).
- **Histórico enriquecido:** export_mode, template_usado, pipeline_stage, tipo_documento.

### Changed

- `ExportService` integrado ao pipeline AI-ready mantendo compatibilidade com modo raw.
- Exportação manual (Ctrl+E) respeita modo e template configurados.

## [2.2.0] - 2026-05-28

### Added

- **Rebrand oficial:** Transcritor Universal → **CortexFlow**.
- **Design System** em `src/ui/design/` (`colors`, `fonts`, `spacing`, `theme_manager`).
- **Fundação AI-ready** em `src/ai_ready/` (estágios raw → clean → ai_ready).
- Header premium com tagline e badge de versão.
- Cards visuais na fila de processamento com destaque por status.
- Sidebar com identidade de marca e tokens de cor consistentes.

### Changed

- Título da janela e cabeçalhos atualizados para CortexFlow v2.2.
- Painel de fila renomeado para "Pipeline de processamento".
- Logger técnico renomeado para `cortexflow`.
- README reescrito com posicionamento de plataforma de conhecimento para IA.

## [2.1.0] - 2026-05-28

### Added

- Botões **Cancelar Fila** e **Abrir pasta de saída**.
- Barra de progresso geral e contadores (total, aguardando, processando, concluídos, erros).
- Preview truncado para arquivos grandes com opção **Carregar texto completo**.
- Log técnico rotativo em `data/logs/app.log`.
- Classificação de erros por item (`error_code` + mensagem amigável).
- Status `cancelado` para itens não processados após cancelamento.
- Histórico com status (`concluído`, `erro`, `parcial`) e mensagens resumidas.

### Fixed

- Bloqueio de início duplicado da fila enquanto já processa.
- Remoção de item selecionado permitida quando não está em processamento.
- Registro de progresso parcial no histórico ao cancelar a fila.

### Changed

- Histórico exibe status e mensagem resumida no painel lateral.

## [2.0.0] - 2026-05-28

### Added

- Arquitetura modular em `src/core`, `src/models` e `src/ui`.
- Fila de transcrições com múltiplos arquivos, status e caminho de saída.
- Serviço Whisper singleton (modelo carregado uma vez e reutilizado).
- Processamento da fila em thread de fundo, sem bloquear a interface.
- Painéis: configurações (esquerda), fila (centro), resultado (inferior).
- Pasta e formato padrão de saída configuráveis (`data/settings.json`).
- Histórico persistido em `data/historico_transcricoes.json`.
- Ponto de entrada `app.py` e migração automática do histórico legado.

### Changed

- Interface reorganizada em CustomTkinter com layout em três áreas.
- Drag and drop adiciona arquivos à fila em vez de substituir o arquivo atual.
- Exportação automática ao concluir cada item da fila.

### Preserved

- Suporte a áudio, vídeo, texto, PDF, DOCX, XLSX e OCR (JPG/PNG).
- Temas System/Light/Dark, idiomas, exportação manual TXT/JSON/MD.
- Atalhos Ctrl+O, Ctrl+T, Ctrl+E, Ctrl+Q.
- Compatibilidade Windows e `app_transcricao.py` como alias legado.
