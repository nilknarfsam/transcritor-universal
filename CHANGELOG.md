# Changelog

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
