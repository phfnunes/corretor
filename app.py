from flask import Flask, request, render_template
import os
import tempfile
import PyPDF2
import docx
from bs4 import BeautifulSoup
import language_tool_python
import unidecode
import logging
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.html'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {ext[1:] for ext in ALLOWED_EXTENSIONS}

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/health')
def health():
    return 'OK', 200

@app.route('/upload', methods=['POST'])
def upload():
    # Check file presence
    if 'file' not in request.files:
        return 'Nenhum arquivo enviado.', 400
        
    uploaded_file = request.files['file']
    
    # Validate file
    if uploaded_file.filename == '':
        return 'Nenhum arquivo selecionado.', 400
        
    if not allowed_file(uploaded_file.filename):
        return 'Formato de arquivo não suportado.', 400
        
    if request.content_length > MAX_FILE_SIZE:
        return 'Arquivo muito grande (máx 5MB).', 413

    try:
        # Process file
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(uploaded_file.filename)[1]) as temp_file:
            uploaded_file.save(temp_file.name)
            logger.info(f"Processing file: {secure_filename(uploaded_file.filename)}")
            
            text = extract_text(temp_file.name)
            if text.startswith('Erro'):
                return text, 400
                
            analysis = analyze_text(text)
            return render_template('resultados.html', 
                                text=text, 
                                analysis=analysis,
                                filename=secure_filename(uploaded_file.filename))

    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return f"Erro interno ao processar arquivo: {str(e)}", 500

def extract_text(file_path):
    try:
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ''.join([page.extract_text() or '' for page in reader.pages])
                if not text.strip():
                    raise ValueError("PDF não contém texto legível")
                return text
                
        elif ext == '.docx':
            doc = docx.Document(file_path)
            return '\n'.join([p.text for p in doc.paragraphs if p.text.strip()])
            
        elif ext == '.doc':
            try:
                import antiword
                return antiword.antiword(file_path)
            except ImportError:
                return "Erro: suporte a .doc requer antiword (instale com pip install antiword)"
            except Exception as e:
                return f"Erro ao ler arquivo .doc: {str(e)}"
                
        elif ext == '.html':
            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'html.parser')
                return soup.get_text()
                
        else:
            return 'Formato de arquivo não suportado.'
            
    except Exception as e:
        return f"Erro ao extrair texto: {str(e)}"

def analyze_text(text):
    try:
        with language_tool_python.LanguageTool('pt-BR') as tool:
            matches = tool.check(text)
            error_list = [f"Linha {m.line+1}, Erro: {m.message}" for m in matches]

            word_count = len(text.split())
            unique_words = len(set(text.split()))
            unaccented = unidecode.unidecode(text)

            return {
                'word_count': word_count,
                'unique_words': unique_words,
                'error_count': len(matches),
                'errors': error_list[:10],
                'unaccented_preview': unaccented[:300]
            }
    except Exception as e:
        logger.error(f"Error in text analysis: {str(e)}")
        return {
            'word_count': 0,
            'unique_words': 0,
            'error_count': 0,
            'errors': [f"Erro na análise: {str(e)}"],
            'unaccented_preview': ""
        }

if __name__ == '__main__':
    app.run(debug=True)
