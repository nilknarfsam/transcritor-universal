# Transcritor Universal 2.0 – Áudio / Vídeo / Texto

GUI moderna (CustomTkinter) para **transcrever áudio e vídeo com Whisper**, **extrair texto de PDFs, DOCX e XLSX**, e **fazer OCR em imagens** (Tesseract). Suporta **fila de transcrições**, **drag & drop**, histórico e exportação em **TXT, JSON e Markdown**.

> Ponto de entrada: `app.py`

---

## Recursos

* **Transcrição (Whisper):** MP3, WAV, M4A, FLAC, MP4, AVI, MOV, MKV
* **Textos:** TXT, PDF, DOCX, XLSX
* **OCR em imagens:** JPG, JPEG, PNG (via Tesseract)
* **Fila:** vários arquivos com status (aguardando, processando, concluído, erro)
* **Saída automática:** mesma pasta do arquivo ou pasta global configurável
* **Idiomas:** detecção automática ou seleção manual (pt, en, es, fr, de, it, ru, zh)
* **UX:** arrastar & soltar, painéis de configuração/fila/resultado, tema escuro/claro
* **Exportação:** TXT, JSON, Markdown (automática e manual)
* **Histórico:** últimas transcrições em `data/historico_transcricoes.json`

---

## Estrutura do projeto

```
app.py
src/
  core/
    transcription_service.py   # Whisper (singleton)
    extraction_service.py      # TXT, PDF, DOCX, XLSX, OCR
    export_service.py
    queue_manager.py
    settings_service.py
  models/
    transcription_job.py
  ui/
    main_window.py
    queue_panel.py
    settings_panel.py
    result_panel.py
data/
  settings.json
  historico_transcricoes.json
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

Compatível com o comando anterior:

```bash
python app_transcricao.py
```

---

## Como usar

1. Abra o app e ajuste **tema**, **idioma** e **formato padrão** no painel esquerdo.
2. **Adicione arquivos** (botão ou drag & drop) — entram na fila.
3. Opcional: defina uma **pasta global de saída** ou deixe na mesma pasta do arquivo.
4. Clique em **Iniciar Fila** para processar todos os itens aguardando.
5. Selecione um item na fila para ver o resultado e exportar manualmente se quiser.
6. Consulte o histórico no painel de configurações.

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

## Changelog

Veja [CHANGELOG.md](CHANGELOG.md).
