# Changelog

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
