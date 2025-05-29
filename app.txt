from flask import Flask, request, render_template
import os
import tempfile
import PyPDF2
import docx
from bs4 import BeautifulSoup
import language_tool_python
import unidecode

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload():
    uploaded_file = request.files['file']
    if uploaded_file.filename != '':
        suffix = os.path.splitext(uploaded_file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            uploaded_file.save(temp_file.name)
            temp_path = temp_file.name

        text = extract_text(temp_path)
        analysis = analyze_text(text)
        os.remove(temp_path)
        return render_template('resultados.html', text=text, analysis=analysis)
    return 'Nenhum arquivo enviado.'

def extract_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            return ''.join([page.extract_text() for page in reader.pages])
    elif ext == '.docx':
        doc = docx.Document(file_path)
        return '\n'.join([p.text for p in doc.paragraphs])
    elif ext == '.html':
        with open(file_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
            return soup.get_text()
    else:
        return 'Formato de arquivo não suportado.'

def analyze_text(text):
    tool = language_tool_python.LanguageTool('pt-BR')
    matches = tool.check(text)
    error_list = [f"Linha {m.line+1}, Erro: {m.message}" for m in matches]
    tool.close()

    word_count = len(text.split())
    unique_words = len(set(text.split()))
    unaccented = unidecode.unidecode(text)

    return {
        'word_count': word_count,
        'unique_words': unique_words,
        'error_count': len(matches),
        'errors': error_list[:10],  # mostra só os 10 primeiros erros
        'unaccented_preview': unaccented[:300]
    }

if __name__ == '__main__':
    app.run(debug=True)
