import os
import random
import time
import PIL
from PIL import Image
import simplejson
from flask import Flask, request, render_template, session, flash, redirect, \
    url_for, jsonify, send_from_directory
from celery import Celery
from werkzeug import secure_filename

from lib.upload_file import uploadfile

app = Flask(__name__)
# app.config['SECRET_KEY'] = 'cvml'
app.config['UPLOAD_FOLDER'] = 'data/'
app.config['THUMBNAIL_FOLDER'] = 'data/thumbnail/'

# Celery configuration
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

# Initialize Celery
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('index.html')   

    return redirect(url_for('index'))

@celery.task(bind=True)
def long_task(self):
    """Background task that runs a long function with progress reports."""
    verb = ['Starting up', 'Booting', 'Repairing', 'Loading', 'Checking']
    adjective = ['master', 'radiant', 'silent', 'harmonic', 'fast']
    noun = ['solar array', 'particle reshaper', 'cosmic ray', 'orbiter', 'bit']
    message = ''
    total = random.randint(10, 50)
    for i in range(total):
        if not message or random.random() < 0.25:
            message = '{0} {1} {2}...'.format(random.choice(verb),
                                              random.choice(adjective),
                                              random.choice(noun))
        self.update_state(state='PROGRESS',
                          meta={'current': i, 'total': total,
                                'status': message})
        time.sleep(1)
    return {'current': 100, 'total': 100, 'status': 'Task completed!',
            'result': 42}

@app.route('/longtask', methods=['POST'])
def longtask():
    task = long_task.apply_async()
    return jsonify({}), 202, {'Location': url_for('taskstatus',
                                                  task_id=task.id)}

@app.route('/status/<task_id>')
def taskstatus(task_id):
    task = long_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)

ALLOWED_EXTENSIONS = set(['jpg', 'jpeg'])

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def gen_file_name(filename):
    """
    If file was exist already, rename it and return a new name
    """

    i = 1
    while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
        name, extension = os.path.splitext(filename)
        filename = '%s_%s%s' % (name, str(i), extension)
        i = i + 1

    return filename

def create_thumbnai(image):
    try:
        basewidth = 80
        img = Image.open(os.path.join(app.config['UPLOAD_FOLDER'], image))
        wpercent = (basewidth/float(img.size[0]))
        hsize = int((float(img.size[1])*float(wpercent)))
        img = img.resize((basewidth,hsize), PIL.Image.ANTIALIAS)
        img.save(os.path.join(app.config['THUMBNAIL_FOLDER'], image))

        return True
    
    except:
        return False    

@app.route("/upload", methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        #pprint (vars(objectvalue))

        if file:
            filename = secure_filename(file.filename)
            filename = gen_file_name(filename)
            mimetype = file.content_type


            if not allowed_file(file.filename):
                result = uploadfile(name=filename, type=mimetype, size=0, not_allowed_msg="Filetype not allowed")

            else:
                # save file to disk
                uploaded_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(uploaded_file_path)

                # create thumbnail after saving
                if mimetype.startswith('image'):
                    create_thumbnai(filename)
                
                # get file size after saving
                size = os.path.getsize(uploaded_file_path)

                # return json for js call back
                result = uploadfile(name=filename, type=mimetype, size=size)
            
            return simplejson.dumps({"files": [result.get_file()]})

    if request.method == 'GET':
        # get all file in ./data directory
        files = [ f for f in os.listdir(app.config['UPLOAD_FOLDER']) if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'],f)) and f not in IGNORED_FILES ]
        
        file_display = []

        for f in files:
            size = os.path.getsize(os.path.join(app.config['UPLOAD_FOLDER'], f))
            file_saved = uploadfile(name=f, size=size)
            file_display.append(file_saved.get_file())

        return simplejson.dumps({"files": file_display})

    return redirect(url_for('index'))

# serve static files
@app.route("/thumbnail/<string:filename>", methods=['GET'])
def get_thumbnail(filename):
    return send_from_directory(app.config['THUMBNAIL_FOLDER'], filename=filename)


@app.route("/data/<string:filename>", methods=['GET'])
def get_file(filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER']), filename=filename)

if __name__ == '__main__':
    app.run(debug=True)                                                                  