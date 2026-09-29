import os
def allowed_file(filename):
    ALLOWED = {'pdf','doc','docx','txt'}
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED
