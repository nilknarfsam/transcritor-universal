# CortexFlow · 3.0.4

> 🎙️ **Ferramenta desktop profissional e totalmente local** para transcrição de áudio e vídeo em lote — otimizada para estruturação de conhecimento e ingestão em IAs como **NotebookLM**, GPT Projects e pipelines RAG.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Whisper](https://img.shields.io/badge/OpenAI-Whisper-412991?logo=openai&logoColor=white)](https://github.com/openai/whisper)
[![Offline](https://img.shields.io/badge/Processamento-100%25%20local-success)]()
[![License](https://img.shields.io/badge/License-Uso%20interno-lightgrey)]()

Transforme horas de áudio, vídeo, PDFs, documentos Office e imagens (OCR) em **texto estruturado** — sem enviar dados para a nuvem. O CortexFlow 3.0.4 consolida uma interface enxuta, fila persistente e motor de transcrição pronto para produção em lote.

---

## ✨ Recursos principais

- **Processamento em lote com fila inteligente e thread-safe** — adicione dezenas de arquivos, acompanhe status em tempo real e retome sessões interrompidas via `data/queue_state.json`.
- **Transcrição 100% offline** utilizando os modelos **OpenAI Whisper** (singleton em memória, progresso real capturado da barra tqdm).
- **Saída em Markdown estruturado** com separação de parágrafos e timestamps precisos **`[MM:SS]`** — adeus ao *wall of text*; blocos legíveis para leitura humana e ingestão em IAs.
- **Interface desktop (GUI) limpa, responsiva e focada em produtividade** — CustomTkinter + drag-and-drop; fila como elemento central (~85% da tela); configurações em modal; resultado em janela secundária.
- **Gerenciamento de cache inteligente (SHA256)** — evita reprocessar arquivos já transcritos; indicadores HIT / MISS / PARTIAL na UI.
- **Extração multimodal** — PDF (`pdfplumber`), DOCX, XLSX, TXT e OCR em imagens via **Tesseract** (`pytesseract`).
- **Exportação flexível** — TXT, JSON e Markdown; modos *Raw*, *Clean*, *AI Ready*, *NotebookLM* e *Study Mode*.
- **Fila persistente e recovery automático** — retoma trabalho após fechar o app ou queda de energia.
- **Atalhos de teclado** — `Ctrl+O` (abrir), `Ctrl+T` (iniciar fila), `Ctrl+E` (exportar), `Ctrl+,` (configurações).

---

## 📋 Pré-requisitos

| Requisito | Obrigatório | Observação |
|-----------|:-----------:|------------|
| **Python 3.10+** | ✅ | Marque *Add Python to PATH* na instalação. [python.org/downloads](https://www.python.org/downloads/) |
| **FFmpeg** | ✅ **Crítico** | **Obrigatório** para Whisper transcrever áudio e vídeo. Deve estar no **PATH do sistema** (Windows). |
| **Tesseract OCR** | ⚠️ | Necessário apenas para imagens (JPG, PNG). [Instalação Windows](https://github.com/UB-Mannheim/tesseract/wiki) |
| **GPU CUDA** | ❌ | Opcional — acelera Whisper; CPU funciona normalmente. |

### ⚠️ FFmpeg no Windows (não pule esta etapa)

Sem FFmpeg no PATH, a transcrição de áudio/vídeo **falhará**. Após instalar:

```powershell
ffmpeg -version
```

Se o comando não for reconhecido, adicione a pasta `bin` do FFmpeg às variáveis de ambiente do Windows (ex.: builds em [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/)).

> 💡 **Dica:** reinicie o terminal (ou o VS Code) após alterar o PATH.

---

## 🚀 Instalação

```bash
# 1. Clonar o repositório
git clone https://github.com/seu-usuario/transcritor-universal.git
cd transcritor-universal

# 2. Criar ambiente virtual
python -m venv .venv

# 3. Ativar o ambiente
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Windows (CMD)
.venv\Scripts\activate.bat
# Linux / macOS
source .venv/bin/activate

# 4. Instalar dependências Python
pip install -r requirements.txt
```

Alternativa no Windows: execute `instalar_dependencias.bat` (se disponível no repositório).

---

## ▶️ Como executar

Na raiz do projeto, com o ambiente virtual ativo:

```bash
python app.py
```

Alias legado compatível: `python app_transcricao.py`

---

## 🛠️ Stack tecnológica

| Camada | Tecnologia |
|--------|------------|
| **Linguagem** | Python 3.10+ |
| **Transcrição** | [OpenAI Whisper](https://github.com/openai/whisper) |
| **Interface** | [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) + [tkinterdnd2](https://github.com/pmgagne/tkinterdnd2) (drag-and-drop) |
| **Documentos** | [pdfplumber](https://github.com/jsvine/pdfplumber), [python-docx](https://python-docx.readthedocs.io/), [openpyxl](https://openpyxl.readthedocs.io/) |
| **OCR** | [Tesseract](https://github.com/tesseract-ocr/tesseract) via [pytesseract](https://github.com/madmaze/pytesseract) |
| **Mídia** | FFmpeg (dependência de sistema) |
| **Imagens** | [Pillow](https://python-pillow.org/) |
| **Persistência** | JSON local em `data/` (settings, fila, cache, histórico, logs) |

---

## 📁 Formatos suportados

| Tipo | Extensões |
|------|-----------|
| Áudio | `.mp3` `.wav` `.m4a` `.flac` |
| Vídeo | `.mp4` `.avi` `.mov` `.mkv` |
| Texto / Office | `.txt` `.pdf` `.docx` `.xlsx` |
| Imagem (OCR) | `.jpg` `.jpeg` `.png` |

---

## 📖 Documentação adicional

| Recurso | Descrição |
|---------|-----------|
| [CHANGELOG.md](CHANGELOG.md) | Histórico de versões e mudanças |
| [agent.md](agent.md) | Contexto técnico e fases de refatoração |
| [docs/CODE_REVIEW_REPORT.md](docs/CODE_REVIEW_REPORT.md) | Relatório da sprint de qualidade |
| [docs/UI_CLEANUP_REPORT.md](docs/UI_CLEANUP_REPORT.md) | Relatório da simplificação UX 3.1 |

---

## 🧪 Testes

```bash
python -m unittest discover -s tests -v
```

---

## 📄 Licença

Consulte o repositório para termos de uso. Processamento 100% local — seus arquivos não saem da máquina.

---

<p align="center">
  <strong>CortexFlow 3.0.4</strong> — transcreva em lote, estruture conhecimento, alimente suas IAs.<br>
  <sub>Feito com 🐍 Python · 🔒 privacidade por design</sub>
</p>
