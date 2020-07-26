from flask import Flask, request, render_template, send_from_directory, flash, redirect, url_for, session, abort, make_response
import os
from werkzeug.utils import secure_filename
import cv2
from shutil import copy2
import json
from werkzeug.security import generate_password_hash, check_password_hash
import MySQLdb
import datetime
# import socket
import re
import httpagentparser
# from device_detector import DeviceDetector, SoftwareDetector
from user_agents import parse
# import uuid
#from OpenSSL import SSL

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
trainedImagePath = os.path.join(APP_ROOT, "train")
TRAIN_FOLDER_mid = os.path.join(APP_ROOT, "trainSmall")
UPLOAD_FOLDER = os.path.join(APP_ROOT, "uploads")
POSTER_FOLDER = os.path.join(APP_ROOT, "poster")
POSTER_SMALL = os.path.join(APP_ROOT, "posterSmall")
POSTER_MID = os.path.join(APP_ROOT, "posterMid")

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif', 'bmp'])

if not os.path.isdir(UPLOAD_FOLDER):
        os.mkdir(UPLOAD_FOLDER)

if not os.path.isdir(trainedImagePath):
        os.mkdir(trainedImagePath)

app = Flask(__name__)

class userFolder:
    def __init__(self):
        self.hostname = request.remote_addr #socket.gethostname()    
        # self.IPAddr = socket.gethostbyname(self.hostname)
        # self.IPAddr = hex(uuid.getnode())
        # print("Your Computer Name is:" + self.hostname)    
        ua = request.environ['HTTP_USER_AGENT']
        # print("Your Computer IP Address is:" + request.environ['HTTP_USER_AGENT'])
        # print(httpagentparser.detect(ua))
        
        user_agent = parse(ua)

        # print(user_agent)
        # print(user_agent.browser)
        # print(user_agent.os)
        # print(user_agent.device)

        self.ua = user_agent.os.family+ '-' +user_agent.device.family+ '-' +user_agent.browser.family+ '-' +user_agent.browser.version_string

        self.user_folder = self.hostname + '-' + self.ua

#app.debug = True
app.secret_key = "super_secret_key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['POSTER_FOLDER'] = POSTER_FOLDER
app.config['POSTER_SMALL']  = POSTER_SMALL
app.config['POSTER_MID']  = POSTER_MID
app.config['TRAIN_FOLDER']  = trainedImagePath
app.config['TRAIN_FOLDER_mid']  = TRAIN_FOLDER_mid
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

## function to check allowed filetype
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Filter list of strings based on another list 
def Filter(string, substr): 
    return [str for str in string if
             any(sub in str for sub in substr)] 

## function to image resize
def image_resize(image, width = None, height = None, inter = cv2.INTER_AREA):
    # initialize the dimensions of the image to be resized and
    # grab the image size
    dim = None
    (h, w) = image.shape[:2]
    
    # if both the width and height are None, then return the
    # original image
    if width is None and height is None:
        return image    

    # # check to see if the width is None
    if width is None:
        # calculate the ratio of the height and construct the
        # dimensions
        r = height / float(h)
        dim = (int(w * r), height)

    # # otherwise, the height is None
    else:
    #     # calculate the ratio of the width and construct the
    #     # dimensions
    #     r = width / float(w)
    #     dim = (width, int(h * r))
        if w > 1200:
            dim = (int(w/1.5), int(h/1.5))
        else:
            dim = (w, h)
    
    # resize the image
    resized = cv2.resize(image, dim, interpolation = inter)

    # return the resized image
    return resized

## function to check image matching and return matching values
def computeImage(img1, img2):
    # Initiate SIFT detector
    # sift = cv2.SIFT()
    sift = cv2.xfeatures2d.SIFT_create()

    # find the keypoints and descriptors with SIFT
    kp1, des1 = sift.detectAndCompute(img1,None)
    kp2, des2 = sift.detectAndCompute(img2,None)

    # FLANN parameters
    FLANN_INDEX_KDTREE = 0
    index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
    search_params = dict(checks=200)   # or pass empty dictionary

    flann = cv2.FlannBasedMatcher(index_params,search_params)

    matches = flann.knnMatch(des1,des2,k=2)

    # Need to draw only good matches, so create a mask
    matchesMask = [[0,0] for i in range(len(matches))]

    # ratio test as per Lowe's paper
    matching_points = 0
    total_points = 0
    for i,(m,n) in enumerate(matches):
        # if m.distance < 0.7*n.distance:
        if m.distance < 0.76*n.distance:
            matchesMask[i]=[1,0]
            matching_points = matching_points + 1
        total_points = total_points + 1

    matching_percentage = (matching_points * 100) / total_points

    return matching_percentage

# 
@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return render_template('page-login.html')
    else:
        ## Train Images
        path, dirs, files = next(os.walk(trainedImagePath))
        file_count = len(files)
        image_names = os.listdir(trainedImagePath)

        # if file_count > 0:
        #     for deleteSelectedImg in files :
        #         destination = os.path.join(app.config['TRAIN_FOLDER'], deleteSelectedImg)
        #         destinationMid = os.path.join(app.config['TRAIN_FOLDER_mid'], deleteSelectedImg)
        #         # Delete image from folder
        #         os.remove(destination)
        #         os.remove(destinationMid)

        ## Poster Images
        pathUp, dirsUp, filesUp = next(os.walk(POSTER_FOLDER))
        file_countUp = len(filesUp)
        image_namesUp = os.listdir(POSTER_FOLDER)

        # if file_countUp > 0:
        #     for deleteSelectedImgUp in filesUp :
        #         destinationUp    = os.path.join(app.config['POSTER_FOLDER'], deleteSelectedImgUp)
        #         destinationMidUp = os.path.join(app.config['POSTER_MID'], deleteSelectedImgUp)
        #         # Delete image from folder
        #         os.remove(destinationUp)
        #         os.remove(destinationMidUp)
        
        return render_template('page-upload-admin.html', filecountUp=file_countUp, filecount=file_count, filesUp=filesUp, files=files)

## check login credentials.
@app.route('/login', methods=['GET', 'POST'])
def do_admin_login():
    # Database connection
    db = MySQLdb.connect(host="localhost", user="alegra6_syed", passwd="smdBAlg%94z", db="alegra6_hdms")
    cur = db.cursor()
    # Select data from table using SQL query
    cur.execute("""SELECT * FROM alegra6_hdms.demo_users""")
    for value in cur.fetchall():
        # username and password
        original_username = value[1]
        originl_password = value[2]
        print(value[2])
    db.close() # close database connection
    if check_password_hash(originl_password, request.form['password']) and request.form['username'] == original_username:
        session['logged_in'] = True
    else:
        flash('Wrong username and password!')
    return redirect(url_for('admin'))

## Logout function
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    # username = ''
    session['logged_in'] = False
    #return redirect(url_for('admin'))
    return redirect(url_for('index'))


## display home page and send required parameters
@app.route('/')
@app.route('/index')
def index():
    user_folder = userFolder().user_folder

    substr = [user_folder]

    ## Train Images
    path, dirs, files = next(os.walk(trainedImagePath))
    # file_count = len(files)
    image_names = os.listdir(trainedImagePath)

    files  = Filter(files, substr)
    file_count = len(files)

    # if file_count > 0:
    #     for deleteSelectedImg in files :
    #         destination = os.path.join(app.config['TRAIN_FOLDER'], deleteSelectedImg)
    #         destinationMid = os.path.join(app.config['TRAIN_FOLDER_mid'], deleteSelectedImg)
    #         # Delete image from folder
    #         os.remove(destination)
    #         os.remove(destinationMid)

    ## Poster Images
    pathUp, dirsUp, filesUp = next(os.walk(POSTER_FOLDER))
    # file_countUp = len(filesUp)
    image_namesUp = os.listdir(POSTER_FOLDER)

    filesUp  = Filter(filesUp, substr)
    file_countUp = len(filesUp)


    # if file_countUp > 0:
    #     for deleteSelectedImgUp in filesUp :
    #         destinationUp    = os.path.join(app.config['POSTER_FOLDER'], deleteSelectedImgUp)
    #         destinationMidUp = os.path.join(app.config['POSTER_MID'], deleteSelectedImgUp)
    #         # Delete image from folder
    #         os.remove(destinationUp)
    #         os.remove(destinationMidUp)
    

    # resp = make_response(render_template('page-upload.html', filecountUp=file_countUp, filecount=file_count, filesUp=filesUp, files=files))
    # resp.set_cookie('email','email')  
    # return resp  
    return render_template('page-upload.html', filecountUp=file_countUp, filecount=file_count, filesUp=filesUp, files=files)

@app.route("/clearTrain", methods=['GET', 'POST'])
def clearTrain():
    if request.method == 'POST':
        path, dirs, files = next(os.walk(trainedImagePath))
        file_count = len(files)
        if file_count > 0:
            for deleteSelectedImg in files :
                destination = os.path.join(app.config['TRAIN_FOLDER'], deleteSelectedImg)
                destinationMid = os.path.join(app.config['TRAIN_FOLDER_mid'], deleteSelectedImg)
                # Delete image from folder
                os.remove(destination)
                os.remove(destinationMid)
    
    return 'done'
    
## upload train images as well as check for existance
@app.route("/upload", methods=['GET', 'POST'])
def upload():
    target  = os.path.join(APP_ROOT, 'uploads/')
    trained = os.path.join(APP_ROOT, 'train/')
    #print(request.url)
    if not os.path.isdir(target):
            os.mkdir(target)
    
    if not os.path.isdir(trained):
            os.mkdir(trained)

    # path, dirs, files = next(os.walk(trainedImagePath))
    # file_count = len(files)
    # if file_count > 0:
    #     for deleteSelectedImg in files :
    #         destination = os.path.join(app.config['TRAIN_FOLDER'], deleteSelectedImg)
    #         destinationMid = os.path.join(app.config['TRAIN_FOLDER_mid'], deleteSelectedImg)
    #         # Delete image from folder
    #         os.remove(destination)
    #         os.remove(destinationMid)

    if request.method == 'POST':
        user_folder = userFolder().user_folder
        substr = [user_folder]
        
        path, dirs, files = next(os.walk(trainedImagePath))
        files  = Filter(files, substr)

        st = str(datetime.datetime.now())

        file_count = len(files)
        if file_count < 3:
            # check if the post request has the file part
            if 'fileToUpload' not in request.files:
                # flash('No file Selected..')
                # return redirect(url_for('index'))
                return 'error: Kein Ordner ausgewählt..'

            fileToUpload = request.files.getlist('fileToUpload')
            
            alreadyTrained = 0
            lessSize = 0
            for file in fileToUpload :
                # if user does not select file, browser also
                # submit an empty part without filename
                if file.filename == '':
                    # flash('No selected file')
                    # return redirect(request.url)
                    return 'error: Kein Ordner ausgewählt..'

                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    # print(filename.rsplit('.', 1)[0])
                    filename = filename.rsplit('.', 1)[0] + ':' + st + '-' + userFolder().user_folder + '.' + filename.rsplit('.', 1)[1]
                    destination = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    print(destination)
                    destinationTrain = os.path.join(app.config['TRAIN_FOLDER_mid'], filename)
                    file.save(destination)
                    copy2(destination, destinationTrain)
                    ## after upload to 'uploads' folder check for duplicates
                    imgT = cv2.imread(destinationTrain)                  # queryImage
                    (h, w) = imgT.shape[:2]
                    if w < 400:
                        lessSize += 1
                    else :
                        ## resize the image
                        imgT = image_resize(imgT, height = 250)
                        # save the resized image
                        cv2.imwrite(destinationTrain, imgT)
                        img1 = cv2.imread(destinationTrain)
                        
                        #Check if image is already trained
                        alreadyTrained = duplicateTrain(destinationTrain, trained, img1, alreadyTrained)
                else:
                    return 'error: Datei nicht erlaubt'

            if alreadyTrained > 0:
                return '{} wurde bereits trainiert.'.format(alreadyTrained)
                # flash('{} Image(s) already Trained.'.format(alreadyTrained))
            if lessSize > 0:
                return '{} Bild(er) zu klein. Bitte mindestens 400 Pixel hochladen.'.format(lessSize)
                # flash('{} Image(s) are of less resolutions. Min. width is 400px.'.format(lessSize))

            # return redirect(url_for('index'))
            return 'success: {} Plakat erfolgreich trainiert .'.format(filename)
        else :
            return 'error: Bitte wählen Sie Max 3 Fotos.'
    # return 'Error'
    return 'error: ERROR'
    
@app.route("/clearPoster", methods=['GET', 'POST'])
def clearPoster():
    if request.method == 'POST':
        pathUp, dirsUp, filesUp = next(os.walk(POSTER_FOLDER))
        file_countUp = len(filesUp)
        print(filesUp)
        if file_countUp > 0:
            for deleteSelectedImg in filesUp :
                destination    = os.path.join(app.config['POSTER_FOLDER'], deleteSelectedImg)
                destinationMid = os.path.join(app.config['POSTER_MID'], deleteSelectedImg)
                # Delete image from folder
                os.remove(destination)
                os.remove(destinationMid)
    
    return 'done'

# Function to check matched images with the big poster
@app.route("/uploaded", methods=['GET', 'POST'])
def uploaded():
    target      = os.path.join(APP_ROOT, 'uploads/')
    poster      = os.path.join(APP_ROOT, 'poster/')
    posterMid = os.path.join(APP_ROOT, 'posterMid/')
    
    if not os.path.isdir(target):
            os.mkdir(target)
    
    if not os.path.isdir(poster):
            os.mkdir(poster)
    
    if request.method == 'POST':
        user_folder = userFolder().user_folder
        substr = [user_folder]

        pathUp, dirsUp, filesUp = next(os.walk(POSTER_FOLDER))
        filesUp  = Filter(filesUp, substr)

        stup = str(datetime.datetime.now())

        file_countUp = len(filesUp)

        if file_countUp < 3:
            # check if the post request has the file part
            if 'fileToUpload' not in request.files:
                # flash('No file Selected...')
                # return redirect(url_for('index'))
                return 'error: Kein Ordner ausgewählt..'

            fileToUpload = request.files.getlist('fileToUpload')

            print(len(fileToUpload))
            
            alreadyTrainedUp  = 0
            lessSize          = 0
            for file in fileToUpload :
                # if user does not select file, browser also
                # submit an empty part without filename
                if file.filename == '':
                    # flash('No selected file')
                    # return redirect(request.url)
                    return 'error: Kein Ordner ausgewählt..'

                if file and allowed_file(file.filename):
                    filename            = secure_filename(file.filename)
                    filename = filename.rsplit('.', 1)[0] + ':' + stup + '-' + userFolder().user_folder + '.' + filename.rsplit('.', 1)[1]

                    destination         = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    destinationSmall    = os.path.join(app.config['POSTER_SMALL'], filename)
                    file.save(destination)
                    # keep the original for final comparision
                    copy2(destination, destinationSmall)
                    
                    imgB = cv2.imread(destination)                  # queryImage

                    # For Compare with trained images need bigger resolutions
                    (h, w) = imgB.shape[:2]
                    if w < 900:
                        lessSize += 1
                    else :
                        ## resize the image
                        imgB = image_resize(imgB, width= 960)
                        # save the resized image
                        cv2.imwrite(destination, imgB)

                    imgT = cv2.imread(destinationSmall)                  # queryImage
                    (hs, ws) = imgT.shape[:2]
                    if ws > 900:
                        imgT = image_resize(imgT, height= 500)
                        # save the resized image
                        cv2.imwrite(destinationSmall, imgT)
                        img1 = cv2.imread(destinationSmall)
                        
                        # Check if image already there
                        alreadyTrainedUp = duplicate(destination, poster, destinationSmall, posterMid, img1, alreadyTrainedUp)
                else:
                    return 'error: Datei nicht erlaubt'

            if alreadyTrainedUp > 0:
                return '{} Bild(er) bereits hochgeladen.'.format(alreadyTrainedUp)
                # flash('{} Image(s) already Uploaded.'.format(alreadyTrainedUp))
            if lessSize > 0:
                return '{} Bild(er) zu klein. Bitte mindestens 900 Pixel hochladen.'.format(lessSize)
                # flash('{} Image(s) are of less resolutions. Min. width of group poster is 900px.'.format(lessSize))
            # return redirect(url_for('index'))
            return 'success: {} Plakat erfolgreich trainiert .'.format(filename)
        else :
            return 'error: Bitte wählen Sie Max 3 Fotos.'

    # return 'Error'
    return 'error: ERROR'

def duplicate(destination, poster, destinationSmall, posterMid, img1, alreadyTrainedUp):
    if not os.listdir("./posterMid"):
        copy2(destinationSmall, posterMid)
        copy2(destination, poster)
    else:
        ## Find All images from the train folder (JPEG, JPG, PNG, GIF and BMP)
        user_folder = userFolder().user_folder
        substr = [user_folder]
        posterSelectedImg    = os.listdir("./posterMid") # eval(request.form['trainSelected'])
        posterSelectedImg    = Filter(posterSelectedImg, substr)

        for file in posterSelectedImg:
            if file.lower().endswith('.jpg') or file.lower().endswith('.jpeg') or file.lower().endswith('.png') or file.lower().endswith('.gif') or file.lower().endswith('.bmp'):
                newImage = os.path.join('posterMid/', file)
                
                img2 = cv2.imread(newImage)     # trainImage
                returnValue = computeImage(img1, img2)
                
                if returnValue >= 75:
                    alreadyTrainedUp += 1
                    return alreadyTrainedUp
        
        copy2(destinationSmall, posterMid)
        copy2(destination, poster)

    return alreadyTrainedUp

def duplicateTrain(destination, trained, img1, alreadyTrained):
    if not os.listdir("./train"):
        copy2(destination, trained)
    else:
        ## Find All images from the train folder (JPEG, JPG, PNG, GIF and BMP)
        user_folder = userFolder().user_folder
        substr = [user_folder]
        trainSelectedImg    = os.listdir("./train") # eval(request.form['trainSelected'])
        trainSelectedImg    = Filter(trainSelectedImg, substr)

        for file in trainSelectedImg:
            if file.lower().endswith('.jpg') or file.lower().endswith('.jpeg') or file.lower().endswith('.png') or file.lower().endswith('.gif') or file.lower().endswith('.bmp'):
                newImage = os.path.join('train/', file)
                # img2 = cv2.imread(newImage, 0)     # trainImage
                img2 = cv2.imread(newImage)     # trainImage
                returnValue = computeImage(img1, img2)
                
                if returnValue >= 75 :
                    alreadyTrained += 1
                    return alreadyTrained
    
        copy2(destination, trained) 
        #move(des..., tra...) to be implemented later

    return alreadyTrained

# Function to check matched images with the big poster
@app.route("/compare", methods=['GET', 'POST'])
def compare():
    if request.method == 'POST':
        pathUp          = {} 
        dirsUp          = {} 
        filesUp         = {}
        file_countUp    = {}
        image_namesUp   = {}
        pathsPoster     = {}
        workerId        = {}
        workerName      = {}
        
        file_countTrain     = {}
        image_namesTrain    = {}

        # imgListS                = {}
        # imgValueS               = {}
        # matchedNumber           = {}

        # imgListNoS              = {}
        # imgValueNoS             = {}
        # noMatchedNumber         = {}

        # imgListPartialS         = {}
        # imgValuePartialS        = {}
        # partialMatchedNumber    = {}

        imgListA            = []
        imgListPartialA         = []
        imgListNoA          = []

        trainSelectedImg    = os.listdir(trainedImagePath) # eval(request.form['trainSelected'])
        posterSelectedImg   = os.listdir(POSTER_FOLDER) # eval(request.form['posterSelected'])

        user_folder = userFolder().user_folder
        substr = [user_folder]

        print('trainSelectedImg')
        print(trainSelectedImg)
        print('posterSelectedImg')
        print(posterSelectedImg)

        trainSelectedImg    = Filter(trainSelectedImg, substr)
        posterSelectedImg   = Filter(posterSelectedImg, substr)

        print('trainSelectedImg')
        print(trainSelectedImg)
        print('posterSelectedImg')
        print(posterSelectedImg)


        if len(trainSelectedImg) > 0 and len(posterSelectedImg) > 0:
            imgListS            = []
            imgValueS           = []
            imgListPartialS         = []
            imgValuePartialS        = []
            imgListNoS          = []
            imgValueNoS         = []
            matchedSize         = 0

            for file in trainSelectedImg: #os.listdir("./train"):
                if file.lower().endswith('.jpg') or file.lower().endswith('.jpeg') or file.lower().endswith('.png') or file.lower().endswith('.gif') or file.lower().endswith('.bmp'):
                    newImage = os.path.join('train/', file)
                    trainImgSmall = os.path.join(app.config['TRAIN_FOLDER_mid'], file)
                    print(newImage)
                    img2 = cv2.imread(newImage)     # trainImage    

                    # matchedSize             = 0
                    # noMatchedSize           = 0
                    # partialMatchedSize      = 0

                    # TO BE IMPLEMENTED FOR COMPARE FUNCTION
                    imgList             = []
                    imgValue            = []
                    imgListPartial      = []
                    imgValuePartial     = []
                    imgListNo           = []
                    imgValueNo          = []
                    
                    # Find All images from the dropbox folder
                    for i in range (len(posterSelectedImg)):

                        destination = os.path.join(app.config['POSTER_FOLDER'], posterSelectedImg[i])
                        destinationMid = os.path.join(app.config['POSTER_MID'], posterSelectedImg[i])
                        print('poster File: '+posterSelectedImg[i])
                        ## load the image from 'poster' folder check for matching
                        img1 = cv2.imread(destination)             # queryImage
                        #img1 = cv2.imread(destination)                  # queryImage

                        returnValue = computeImage(img2, img1)
                        print(returnValue)

                        if returnValue >= 2.65 :
                            # matchedSize += 1
                            # if returnValue >= 1.63 :
                            imgList.append(posterSelectedImg[i])
                            imgListA.append(posterSelectedImg[i])
                            imgValue.append(str(round(returnValue, 2)))

                        elif returnValue >= 1.85 and returnValue <=2.64 :
                            # if returnValue >= 1.63 :
                            # partialMatchedSize += 1
                            imgListPartial.append(posterSelectedImg[i])
                            imgListPartialA.append(posterSelectedImg[i])

                            imgValuePartial.append(str(round(returnValue, 2)))
                        
                        else:
                            # noMatchedSize += 1
                            imgListNo.append(posterSelectedImg[i])
                            imgListNoA.append(posterSelectedImg[i])

                            imgValueNo.append(str(round(returnValue, 2)))

                    imgListS.append(imgList)
                    imgValueS.append(imgValue)
                    imgListPartialS.append(imgListPartial)
                    imgValuePartialS.append(imgValuePartial)
                    imgListNoS.append(imgListNo)
                    imgValueNoS.append(imgValueNo)
                
                                
            # subset & unique
            imgListA         = list(set(imgListA))
            imgListPartialA  = list(set(imgListPartialA) - set(imgListA))      #partial - match only partial display
            imgListNoA       = list(set(imgListNoA) - set(imgListA))           #No_Match - match only partial+nomatch display
            imgListNoA       = list(set(imgListNoA) - set(imgListPartialA))    #No_Match - partial only nomatch display

            # print(imgListS)
            # print(imgListNoS)
            # print(imgListPartialA)
            # print(imgListPartialS)
            # imgListPartialA = ['IMG_8524.JPG','DSCF1414.JPG']
            # imgListPartialS = [[], ['IMG_8524.JPG', 'DSCF1414.JPG'], []]

            # print('--------------------------------')

            # # Delete image from train folder
            
            # # Delete image from poster folder

            path, dirs, files = next(os.walk(trainedImagePath))
            files    = Filter(files, substr)
            file_count = len(files)
            if file_count > 0:
                for deleteSelectedImg in files :
                    destination = os.path.join(app.config['TRAIN_FOLDER'], deleteSelectedImg)
                    destinationMid = os.path.join(app.config['TRAIN_FOLDER_mid'], deleteSelectedImg)
                    # Delete image from folder
                    os.remove(destination)
                    os.remove(destinationMid)

            pathUp, dirsUp, filesUp = next(os.walk(POSTER_FOLDER))
            filesUp   = Filter(filesUp, substr)
            file_countUp = len(filesUp)
            print(filesUp)
            if file_countUp > 0:
                for deleteSelectedImg in filesUp :
                    destination    = os.path.join(app.config['POSTER_FOLDER'], deleteSelectedImg)
                    destinationMid = os.path.join(app.config['POSTER_MID'], deleteSelectedImg)
                    # Delete image from folder
                    os.remove(destination)
                    os.remove(destinationMid)
            
            ## display output 
            return render_template("page-result.html", matchedSize=matchedSize, matchedImage=imgListS, nomatchedImage=imgListNoA, partialMatchedImage=imgListPartialA, partialMatchedList=imgListPartialS, matchedValue=imgValueS, nomatchedValues=imgValueNoS, image_poster=posterSelectedImg, image_train=trainSelectedImg)
        else:
            flash('Keine zu vergleichenden Bilder')
            return redirect(url_for('index'))

    return 'Error'

# Function to delete images with the popup
@app.route("/delete", methods=['GET', 'POST'])
def delete():
    if request.method == 'POST':
        deleteSelectedImg       = request.form['deleteImage']
        deleteFrom              = request.form['deleteFrom']
        
        if deleteFrom == 'poster' :
            destination    = os.path.join(app.config['POSTER_FOLDER'], deleteSelectedImg)
            destinationMid = os.path.join(app.config['POSTER_MID'], deleteSelectedImg)
        else :
            destination = os.path.join(app.config['TRAIN_FOLDER'], deleteSelectedImg)
            destinationMid = os.path.join(app.config['TRAIN_FOLDER_mid'], deleteSelectedImg)
        
        # Delete image from folder
        os.remove(destination)
        os.remove(destinationMid)
            
        flash('Gelöscht')
        return redirect(url_for('admin'))

    return 'Error'

## to display output images
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

## to display Trained Images
@app.route('/train/<filename>')
def send_image(filename):
    return send_from_directory("train", filename)

## to display Poster Images
@app.route('/poster/<filename>')
def poster_image(filename):
    return send_from_directory("poster", filename)


if __name__ == "__main__":
    #app.run(debug=True)
    app.run(port=8995, host='0.0.0.0', debug=True)
    # context = ('/home/alegra6/ssl/certs/alegralabs_com_bf7d3_87cf3_1597881599_f862c2193902a11e55d62905cc465e4a.crt', '/home/alegra6/ssl/keys/bf7d3_87cf3_2ac6c15042a98edc33c9c8e3ae40a189.key') #certificate and key files
    # app.run(port=8995, host='0.0.0.0', ssl_context=context)
