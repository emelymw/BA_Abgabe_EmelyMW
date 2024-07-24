from flask import Blueprint, request, render_template, flash, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
import os
import json

from openapi_spec_validator import validate, OpenAPIV30SpecValidator, OpenAPIV31SpecValidator
from openapi_spec_validator.readers import read_from_filename

from .GraphGenerator import GraphGenerator
from .SequenceGenerator import SequenceGenerator

basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
ALLOWED_EXTENSIONS = {'json', 'yaml'}

bp = Blueprint("openapi", __name__, url_prefix="/")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/')
def home():
    return redirect(url_for('openapi.upload'))

@bp.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))

            # Check if the file is a valid 3.0/3.1 openapi_file
            spec_dict, base_uri = read_from_filename(os.path.join(UPLOAD_FOLDER, filename))
            openapi_version = spec_dict.get('openapi', '')

            if openapi_version.startswith('3.0'):
                validator_class = OpenAPIV30SpecValidator
            elif openapi_version.startswith('3.1'):
                validator_class = OpenAPIV31SpecValidator
            else:
                flash('Last uploaded file was not a valid 3.0/3.1 OpenAPI File')
                return render_template('openapi/form.html')
            try:
                validate(spec_dict, cls=validator_class)
            except:
                flash('Last uploaded file was not a valid 3.0/3.1 OpenAPI File')
                return render_template('openapi/form.html')

            gg = GraphGenerator(os.path.join(UPLOAD_FOLDER, filename))
            gg.create_graph()
 
            return redirect(url_for('openapi.details'))
        
    return render_template('openapi/form.html')

@bp.route('/details', methods=['GET', 'POST'])
def details():
    sg = SequenceGenerator()
    object = sg.get_infos()

    if request.method == 'POST':
        button = request.form.get('button')
        if button == 'object_crud':
            result = sg.get_object_crud()
            with open(os.path.join(UPLOAD_FOLDER, 'object_crud.json'), 'w') as output_file:
                json.dump(result, output_file, indent = 4) 
            return redirect(url_for('openapi.download_file', name='object_crud.json'))
        elif button == 'object_list':
            result = sg.get_object_list()
            with open(os.path.join(UPLOAD_FOLDER, 'object_list.json'), 'w') as output_file:
                json.dump(result, output_file, indent = 4) 
            return redirect(url_for('openapi.download_file', name='object_list.json'))
        elif button == 'endpoint_list':
            result = sg.get_endpoint_list()
            with open(os.path.join(UPLOAD_FOLDER, 'endpoint_list.json'), 'w') as output_file:
                json.dump(result, output_file, indent = 4) 
            return redirect(url_for('openapi.download_file', name='endpoint_list.json'))

    return render_template('openapi/details.html', object=object)

@bp.route('/download/<name>')
def download_file(name):
    return send_from_directory(UPLOAD_FOLDER, name)
