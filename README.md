# Transcritor Universal – Áudio / Vídeo / Texto

Uma GUI simples e moderna (CustomTkinter) para **transcrever áudio e vídeo com Whisper**, **extrair texto de PDFs, DOCX e XLSX**, e **fazer OCR em imagens** (Tesseract). Suporta **drag & drop**, histórico de transcrições e exportação em **TXT, JSON e Markdown**.

> Arquivo principal: `app_transcricao.py`

---

## ✨ Recursos

* **Transcrição (Whisper):** MP3, WAV, M4A, FLAC, MP4, AVI, MOV, MKV
* **Textos:** TXT, PDF, DOCX, XLSX
* **OCR em imagens:** JPG, JPEG, PNG (via Tesseract)
* **Idiomas:** detecção automática ou seleção manual (pt, en, es, fr, de, it, ru, zh)
* **UX:** arrastar & soltar, barra de progresso, mensagens de status
* **Exportação:** TXT, JSON, Markdown
* **Histórico:** lista as últimas transcrições

---

## 🧰 Requisitos (Windows)

### 1) Python 3.10+

* Baixe e instale o Python (marque **“Add Python to PATH”**).
* Link: [https://www.python.org/downloads/](https://www.python.org/downloads/)

### 2) FFmpeg (para Whisper)

* Faça o download dos binários para Windows e **adicione o diretório `bin` ao PATH**.
* Página oficial: [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
* Builds recomendadas para Windows (Gyan): [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)

### 3) Tesseract OCR (para OCR em imagens)

* Instale o **Tesseract** para Windows (**inclua os idiomas** desejados, ex.: *Portuguese*).
* Documentação (downloads): [https://tesseract-ocr.github.io/tessdoc/Downloads.html](https://tesseract-ocr.github.io/tessdoc/Downloads.html)
* Instalador Windows (UB Mannheim): [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)

> Após instalar, adicione `C:\Program Files\Tesseract-OCR\` ao PATH.

### 4) Dependências Python

Crie um *virtualenv* (opcional) e instale as dependências:

```bash
pip install -r requirements.txt
```

Conteúdo recomendado do `requirements.txt`:

```txt
tkinterdnd2
customtkinter
openai-whisper
pdfplumber
python-docx
openpyxl
pillow
pytesseract
```

---

## 🚀 Como executar

Na pasta do projeto:

```bash
python app_transcricao.py
```

---

## 🖱️ Como usar

1. Abra o app e escolha um **tema** (System/Light/Dark).
2. Arraste e solte um arquivo *ou* clique em **“Escolher arquivo”**.
3. Se quiser, selecione o **idioma** (ou deixe em **auto**).
4. Clique em **“Iniciar Transcrição”**.
5. Exporte em TXT, JSON ou Markdown.
6. Veja suas últimas transcrições no histórico.

---

## ⌨️ Atalhos

* **Ctrl + O** → Abrir arquivo
* **Ctrl + T** → Iniciar transcrição
* **Ctrl + E** → Exportar
* **Ctrl + Q** → Fechar app

---

## 📁 Formatos suportados

* **Áudio:** `.mp3`, `.wav`, `.m4a`, `.flac`
* **Vídeo:** `.mp4`, `.avi`, `.mov`, `.mkv`
* **Texto:** `.txt`, `.pdf`, `.docx`, `.xlsx`
* **Imagem (OCR):** `.jpg`, `.jpeg`, `.png`

---

## 🛠️ Configuração PATH no Windows

### FFmpeg

1. Extraia o ZIP (ex.: `C:\ffmpeg\`).
2. Adicione `C:\ffmpeg\bin` ao PATH.
3. Teste:

   ```bash
   ffmpeg -version
   ```

### Tesseract

1. Instale (ex.: `C:\Program Files\Tesseract-OCR\`).
2. Adicione ao PATH.
3. Teste:

   ```bash
   tesseract --version
   ```

Se necessário, configure no código:

```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

---

## ❗ Problemas comuns

* **Whisper não instalado** → `pip install -r requirements.txt`
* **ffmpeg not found** → FFmpeg não está no PATH
* **tesseract not installed** → Tesseract não está no PATH
* **PDF sem texto** → PDF é imagem, use OCR
