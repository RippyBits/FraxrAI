from flask import send_from_directory
from flask import Flask, flash, request, redirect, url_for
from werkzeug.utils import secure_filename
from flask import render_template
from url_utils import get_base_url
import os
import torch

# setup the webserver
# port may need to be changed if there are multiple flask servers running on same server
port = 50234
base_url = get_base_url(port)

# if the base url is not empty, then the server is running in development, and we need to specify the static folder so that the static files are served
if base_url == '/':
    app = Flask(__name__)
else:
    app = Flask(__name__, static_url_path=base_url+'static')

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

model = torch.hub.load("ultralytics/yolov5", "custom", path = 'best.pt', force_reload=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route(f'{base_url}', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
#             flash('No selected file')
            return redirect(request.url)

        if file and allowed_file(file.filename): 
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('uploaded_file',
                                    filename=filename))

    return render_template('newhome.html')                           # Change for different html


@app.route(f'{base_url}/uploads/<filename>')
def uploaded_file(filename):
    here = os.getcwd()
    image_path = os.path.join(here, app.config['UPLOAD_FOLDER'], filename)
    results = model(image_path, size=416)
    if len(list(results.pandas().xyxy[0]['confidence'])) > 0: # If theres a fracture detected
        results.print() 
        save_dir = os.path.join(here, app.config['UPLOAD_FOLDER'])
        results.save(save_dir=save_dir)
        def and_syntax(alist):
            # Adds proper grammar for list of fractures
            # NOTE: Might not be necessary since only one type of label # I think this is for amount of fractures bc of the code on line 86 after the for loop
            if len(alist) == 1:
                alist = "".join(alist)
                return alist
            elif len(alist) == 2:
                alist = " and ".join(alist)
                return alist
            elif len(alist) > 2:
                alist[-1] = "and " + alist[-1]
                alist = ", ".join(alist)
                return alist
            else:
                return # I think this is for null images
        confidences = list(results.pandas().xyxy[0]['confidence'])
        # confidences: rounding and changing to percent, putting in function
        format_confidences = []
        for percent in confidences:
            #loops bc multiple fractures possible
            format_confidences.append(str(round(percent*100)) + '%')
        format_confidences = and_syntax(format_confidences) # 

        labels = list(results.pandas().xyxy[0]['name'])
        # labels: sorting and capitalizing, putting into function
        labels = set(labels)
        if len(labels) == 0:
            num_labels = ""
        else:
            num_labels= int(len(confidences))
            if num_labels > 1:
                labels = ["Fractures"]
        labels = [fracture.capitalize() for fracture in labels]
        labels = and_syntax(labels)
        return render_template('results.html', confidences=format_confidences, labels=labels,
                               old_filename=filename,
                               filename=filename, num_labels=num_labels)
    else: #If there's no fractures found
        found = False
        return render_template('results.html', labels='No Fractures', old_filename=filename, filename=filename)


@app.route(f'{base_url}/uploads/<filename>', methods=['GET','POST'])
def results(filename):
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)


        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('uploaded_file',
                                 filename=filename))

    return render_template('results.html')


@app.route(f'{base_url}/uploads/<path:filename>')
def files(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

# define additional routes here
# for example:
# @app.route(f'{base_url}/team_members')
# def team_members():
#     return render_template('team_members.html') # would need to actually make this page

if __name__ == '__main__':
    # IMPORTANT: change url to the site where you are editing this file.
    website_url = 'cocalc23.ai-camp.dev' #cocalc23.ai-camp.dev
    
    print(f'Try to open\n\n    https://{website_url}' + base_url + '\n\n')
    app.run(host = '0.0.0.0', port=port, debug=True)
