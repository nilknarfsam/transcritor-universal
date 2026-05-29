# CortexFlow — Contexto Global do Agente

> **Fonte de verdade** para assistentes de IA e desenvolvedores.  
> **Regra:** ler este arquivo **antes** de iniciar qualquer tarefa; **atualizar** ao concluir.

---

## 1. Visão Geral

**CortexFlow** (repositório `transcritor-universal`) é uma aplicação desktop **Python 3.10+** para transformar conteúdos brutos — áudio, vídeo, PDF, DOCX, XLSX, TXT e imagens (OCR) — em texto e artefatos exportáveis (TXT, JSON, Markdown), com pipeline opcional **AI-ready** (Clean, AI Ready, NotebookLM, Study Mode).

- **Processamento:** 100% local — **OpenAI Whisper** (áudio/vídeo), **pdfplumber / python-docx / openpyxl** (documentos), **Tesseract** via **pytesseract** (imagens). Sem APIs externas de IA.
- **Interface:** GUI **CustomTkinter** + drag-and-drop (`tkinterdnd2`). Entrada: `app.py` (alias legado: `app_transcricao.py`).
- **Versão atual da UI:** **3.0.4 — Simplificação Radical** — fila de transcrição como foco absoluto (~85% da área); toolbar superior com ações em lote; configurações em modal; resultado em janela secundária. Painéis avançados arquivados em `src/ui/legacy_ui/`.
- **Orquestração:** fila persistente (`data/queue_state.json`), cache SHA256 (`src/cache/`), histórico e settings em `data/`.
- **Arquivos centrais do motor:**
  - `src/core/queue_manager.py` — orquestra fila, cache, export e pós-processamento (biblioteca, grafo, datasets).
  - `src/core/transcription_service.py` — singleton Whisper.
  - `src/core/extraction_service.py` — extração de documentos e OCR.
  - `src/core/export_service.py` + `src/ai_ready/` — pipeline de exportação.
  - `src/ui/main_window.py` — shell da GUI.

**Dependências de sistema:** FFmpeg (PATH), Tesseract OCR (PATH). Ver `README.md` e `requirements.txt`.

---

## 2. Regras de Operação (Sempre ativas)

1. **Idioma:** comunicar com o usuário e documentar tudo em **Português (PT-BR)**.
2. **Commits locais:** ao finalizar alterações **funcionais** (ou documentação operacional acordada, como este arquivo), registrar no Git:
   - `git add` dos arquivos relevantes (evitar secrets: `.env`, credenciais).
   - `git commit -m "refatoração: [descrição]"` ou prefixo adequado (`docs:`, `fix:`, `feat:`) conforme o escopo.
   - Usar mensagem clara em PT-BR ou inglês técnico consistente com o histórico do repo.
3. **NUNCA** executar `git push` — apenas commits locais, salvo instrução explícita futura em contrário.
4. **Relatório final:** ao encerrar cada interação/tarefa, entregar relatório detalhado do que foi alterado (arquivos, comportamento, riscos, próximos passos).
5. **Leitura obrigatória:** antes de codar, reler este `agent.md` e alinhar com o **Estado Atual / Fases** e o **Log de Progresso**.
6. **Escopo:** mudanças mínimas e focadas; seguir convenções existentes; não refatorar áreas não solicitadas.
7. **Segurança Git:** não alterar `git config`; não usar `--no-verify` nem force push; não commitar binários grandes desnecessários na raiz.

---

## 3. Estado Atual / Fases de Refatoração

| Item | Valor |
|------|--------|
| Versão UI | **3.0.4** (CortexFlow — Simplificação Radical / Fila em foco) |
| Branch / remoto | Verificar com `git status` antes de cada tarefa |
| Testes automatizados | `tests/test_knowledge_pipeline.py` (unittest); ampliar cobertura na Fase 4 |
| Principal débito técnico | Tooling (pyproject/CI); contratos `Protocol` para engines (opcional) |
| Sprint Qualidade (PEP 8 / docs / bugs) | **Concluída** — ver `docs/CODE_REVIEW_REPORT.md` |

### Fase 1 — Desacoplar o QueueManager (prioridade alta)

- [x] Extrair processamento de job para `src/core/job_processor.py` (`JobProcessor`, `QueueRunContext`).
- [x] `QueueManager` (~370 linhas): fila, seleção, threading, persistência, callbacks UI; delega `JobProcessor.process()`.
- [x] Pós-processamento de conhecimento condicionado por feature flag (Fase 2).

### Fase 2 — Feature flags (prioridade alta)

- [x] `features.knowledge_pipeline` em `data/settings.json` (padrão `false`) via `SettingsService`.
- [x] `JobProcessor._run_knowledge_post_processing` — biblioteca, grafo e datasets só se `should_run_knowledge_pipeline()`.
- [x] Modos `ai_ready`, `notebooklm`, `study_mode` ativam pipeline temporariamente se a flag estiver desligada; aviso na UI ao selecionar o modo.
- [x] Checkbox em Configurações avançadas para ligar o pipeline de forma persistente.

### Fase 3 — Testes básicos e otimização de boot (prioridade média)

- [x] Testes unitários (`unittest`): `tests/test_knowledge_pipeline.py` — `should_run_knowledge_pipeline`, modos de exportação, flag on/off.
- [x] Lazy loading de `get_library()` na UI: controles de biblioteca só ao abrir configurações avançadas (ou se `knowledge_pipeline` já estiver `true` no boot).
- [ ] Contratos `Protocol` para `TranscriptionEngine`, `TextExtractor`, estágios de export (opcional / fase posterior).
- [ ] Testes adicionais: `export_service`, `job_errors`, cache lookup, serialização da fila.

### Sprint UX 3.1 — Simplificação Radical da Interface

- [x] Remover sidebar (`BrandSidebar`) e header de marca da tela principal.
- [x] Toolbar superior: Adicionar, Remover, Limpar, Iniciar, Cancelar, Abrir Pasta, Configurações.
- [x] Fila como elemento principal (~85% da área) com colunas: Arquivo, Tipo, Status, Progresso, Saída, Tempo.
- [x] Detalhes compactos do item (Nome, Status, Cache, Saída).
- [x] Remover `ResultPanel` embutido; botão «Visualizar Resultado» abre `ResultViewerWindow`.
- [x] Configurações em modal (`SettingsModal`); avançadas recolhidas.
- [x] Status bar: Total | Aguardando | Processando | Concluídos | Erros.
- [x] Arquivar painéis em `src/ui/legacy_ui/` (Biblioteca, Grafo, Estudo, Datasets, Conhecimento).
- [x] Relatório: `docs/UI_CLEANUP_REPORT.md`.

### Sprint Qualidade — PEP 8, Docstrings e Bug Hunt (2026-05-29)

- [x] PEP 8 e limpeza de imports em `src/core/` e `src/ui/` (fila e shell).
- [x] Docstrings e type hints nos serviços principais (`QueueManager`, `JobProcessor`, `TranscriptionService`, etc.).
- [x] Correções: PIL/workbook com liberação de recursos; `RLock` na fila; `unload_model()` ao fim da fila; fallback de encoding em TXT.
- [x] Relatório: `docs/CODE_REVIEW_REPORT.md`.
- [x] Commits locais separados (PEP8, docs, fix) — sem push.

### Fase 4 — Tooling e empacotamento (prioridade média)

- `pyproject.toml` + lockfile (uv/poetry).
- CI mínimo (lint + testes).
- Limpar artefatos na raiz do repo (ffmpeg/tesseract zip, histórico legado duplicado).

### Fase 5 — Melhorias operacionais (prioridade baixa)

- CLI opcional reutilizando o mesmo `JobProcessor`.
- Progresso real do Whisper (callbacks) vs. marcos fixos de `job_progress`.
- Paralelismo seletivo para jobs leves (documentos) — com cuidado em GPU/RAM do Whisper.

---

## 4. Log de Progresso

Registro cronológico (mais recente no topo).

| Data | Tarefa | Resultado |
|------|--------|-----------|
| 2026-05-29 | Sprint Qualidade — PEP 8, docs, bug hunt | Varredura `core/` + `ui/`; `RLock` na fila; `unload_model()`; PIL/XLSX/TXT; `docs/CODE_REVIEW_REPORT.md`; 3 commits locais. |
| 2026-05-29 | Hotfix UX 3.1 — erro aos 5% | `update_job` fazia `refresh()` total a cada `on_notify` (5%); substituído por update in-place da linha. Callbacks UI protegidos em `QueueManager` + logging. FFmpeg vs FILE_NOT_FOUND corrigido em `job_errors`. Commit `fix: corrigir crash de atualização de UI aos 5% do processamento`. |
| 2026-05-29 | Hotfix UX 3.1 — filedialog e callbacks | Modal liberava `_panel` destruído ao fechar; `refresh_history()` crashava na conclusão da fila. File dialog sem `parent` e sem defer. Commit `fix: corrigir travamento de filedialog e callbacks de UI quebrados`. |
| 2026-05-29 | Sprint UX 3.1 — Simplificação Radical | UI 3.0.4: fila em foco, toolbar, modal de config, resultado em janela secundária, legacy_ui, `docs/UI_CLEANUP_REPORT.md`; commits locais da sprint. |
| 2026-05-29 | Fase 3 — Testes e boot | `tests/test_knowledge_pipeline.py`; lazy load de biblioteca em `settings_panel.py`; commit `refatoração: testes knowledge_pipeline e lazy boot (Fase 3)`. |
| 2026-05-29 | Fase 2 — Feature flags | `features.knowledge_pipeline` (default false); pós-processamento condicional no `JobProcessor`; aviso + checkbox na UI; commit `refatoração: feature flag knowledge_pipeline (Fase 2)`. |
| 2026-05-29 | Fase 1 — Desacoplar `QueueManager` | Novo `src/core/job_processor.py` com pipeline de job (cache, Whisper/OCR, export, biblioteca); `queue_manager.py` reduzido a orquestração de fila + worker; commit `refatoração: extrair JobProcessor do QueueManager`. |
| 2026-05-29 | Criação do `agent.md` | Fonte de verdade inicial; fases de refatoração documentadas; commit local `docs: adicionar agent.md como fonte de verdade do projeto`. |

---

## Referências rápidas

- Documentação do produto: `README.md`, `CHANGELOG.md`
- Dependências Python: `requirements.txt`
- Dados em runtime: `data/` (settings, fila, cache, logs, library, datasets, knowledge_graph)
- Testes: `python -m unittest discover -s tests -v`
- Relatório de arquitetura: conversa inicial de análise estrutural (maio/2026) — resumo incorporado nas fases acima.
