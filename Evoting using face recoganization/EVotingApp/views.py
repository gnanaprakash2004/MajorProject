from django.shortcuts import render
from django.template import RequestContext
from django.contrib import messages
import pymysql
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
import os
from Blockchain import *
from Block import *
from datetime import date
import cv2
import numpy as np
import base64
import random
from datetime import datetime
from PIL import Image
import smtplib 
from email.message import EmailMessage
import pickle

global username, password, contact, address
global classifier
global email_id
global otp

blockchain = Blockchain()
if os.path.exists('blockchain_contract.txt'):
    with open('blockchain_contract.txt', 'rb') as fileinput:
        blockchain = pickle.load(fileinput)
    fileinput.close()

face_detection = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
recognizer = cv2.face_LBPHFaceRecognizer.create()

def AddParty(request):
    if request.method == 'GET':
        return render(request, 'AddParty.html', {})

def index(request):
    if request.method == 'GET':
        return render(request, 'index.html', {})

def Login(request):
    if request.method == 'GET':
        return render(request, 'Login.html', {})

def CastVote(request):
    if request.method == 'GET':
        return render(request, 'CastVote.html', {})

def Register(request):
    if request.method == 'GET':
        return render(request, 'Register.html', {})

def Admin(request):
    if request.method == 'GET':
        return render(request, 'Admin.html', {})

def WebCam(request):
    if request.method == 'GET':
        data = str(request)
        formats, imgstr = data.split(';base64,')
        imgstr = imgstr[0:(len(imgstr)-2)]
        data = base64.b64decode(imgstr)
        if os.path.exists("EVotingApp/static/photo/test.png"):
            os.remove("EVotingApp/static/photo/test.png")
        with open('EVotingApp/static/photo/test.png', 'wb') as f:
            f.write(data)
        context = {'data': "done"}
        return HttpResponse("Image saved")

def checkUser(name):
    flag = 0
    for i in range(len(blockchain.chain)):
        if i > 0:
            b = blockchain.chain[i]
            data = b.transactions[0]
            print(data)
            arr = data.split("#")
            if arr[0] == name:
                flag = 1
                break
    return flag

def getOutput(status):
    # Updated HTML using Bootstrap classes for responsive table
    output = f'<div class="container mt-4"><h3 class="mb-4">{status}</h3>'
    output += '<div class="table-responsive"><table class="table table-striped table-bordered text-center">'
    output += ('<thead class="thead-dark"><tr>'
               '<th>Candidate Name</th>'
               '<th>Party Name</th>'
               '<th>Area Name</th>'
               '<th>Image</th>'
               '<th>Cast Vote Here</th>'
               '</tr></thead><tbody>')
    con = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', database='evoting', charset='utf8')
    with con:
        cur = con.cursor()
        cur.execute("select * FROM addparty")
        rows = cur.fetchall()
        for row in rows:
            cname = row[0]
            pname = str(row[1])
            area = row[2]
            output += '<tr>'
            output += f'<td>{cname}</td>'
            output += f'<td>{pname}</td>'
            output += f'<td>{area}</td>'
            output += f'<td><img src="/static/parties/{cname}.png" class="img-fluid" style="max-width:200px;"></td>'
            output += f'<td><a href="FinishVote?id={cname}" class="btn btn-primary">Click Here</a></td>'
            output += '</tr>'
    output += '</tbody></table></div></div>'
    return output

def sendEmail():
    global email_id
    global otp
    msg = EmailMessage()
    msg.set_content("Your OTP is : " + str(otp))
    msg['Subject'] = 'E-Voting OTP'
    msg['From'] = "myprojectstp@gmail.com"
    msg['To'] = email_id
    print(email_id)
    
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login("myprojectstp@gmail.com", "paxgxdrhifmqcrzn")
    s.send_message(msg)
    s.quit()

def FinishVote(request):
    if request.method == 'GET':
        global username
        cname = request.GET.get('id', False)
        today = date.today()
        data = str(username) + "#" + str(cname) + "#" + str(today)
        blockchain.add_new_transaction(data)
        hash = blockchain.mine()
        b = blockchain.chain[len(blockchain.chain)-1]
        print("Previous Hash : " + str(b.previous_hash) + " Block No : " + str(b.index) + " Current Hash : " + str(b.hash))
        bc = "Previous Hash : " + str(b.previous_hash) + "<br/>Block No : " + str(b.index) + "<br/>Current Hash : " + str(b.hash)
        blockchain.save_object(blockchain, 'blockchain_contract.txt')
        context = {'data': f'<div class="container mt-4"><p class="lead">Your Vote Accepted</p><p>{bc}</p></div>'}
        return render(request, 'UserScreen.html', context)

def getUserImages():
    names = []
    ids = []
    faces = []
    dataset = "EVotingApp/static/profiles"
    count = 0
    for root, dirs, directory in os.walk(dataset):
        for j in range(len(directory)):
            pilImage = Image.open(os.path.join(root, directory[j])).convert('L')
            imageNp = np.array(pilImage, 'uint8')
            name = os.path.splitext(directory[j])[0]
            names.append(name)
            faces.append(imageNp)
            ids.append(count)
            count += 1
    print(str(names) + " " + str(ids))
    return names, ids, faces

def getName(predict, ids, names):
    name = "Unable to get name"
    for i in range(len(ids)):
        if ids[i] == predict:
            name = names[i]
            break
    return name

def ValidateUser(request):
    if request.method == 'POST':
        global username
        global otp
        option = 0
        status = "unable to predict user"
        img = cv2.imread('EVotingApp/static/photo/test.png')
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_detection.detectMultiScale(img, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30), flags=cv2.CASCADE_SCALE_IMAGE)
        status = "Unable to predict. Please retry"
        # Sort faces in descending order of area and select the largest face
        faces = sorted(faces, reverse=True, key=lambda x: (x[2] - x[0]) * (x[3] - x[1]))[0]
        (fX, fY, fW, fH) = faces
        face_component = gray[fY:fY + fH, fX:fX + fW]
        if face_component is not None:
            names, ids, face_images = getUserImages()
            recognizer.train(face_images, np.asarray(ids))
            predict, conf = recognizer.predict(face_component)
            print(str(predict) + " === " + str(conf))
            if conf < 80:
                validate_user = getName(predict, ids, names)
                print(str(validate_user) + " " + str(username))
                if validate_user == username:
                    status = "success"
        else:
            status = "Unable to detect face"
        if status == "success":
            flag = checkUser(username)
            if flag == 0:
                option = 1
        if option == 1:
            otp = random.randint(1000, 5000)
            print(otp)
            sendEmail()
            context = {'data': "OTP sent to your mail"}
            return render(request, 'OTPValidation.html', context)
        else:
            context = {'data': status}
            return render(request, 'UserScreen.html', context)

def OTPAction(request):
    if request.method == 'POST':
        global otp
        otp_value = request.POST.get('t1', False)
        if otp_value == str(otp):
            output = getOutput('OTP Validation Successful')
            context = {'data': output}
            return render(request, 'VotePage.html', context)
        else:
            context = {'data': 'Invalid OTP'}
            return render(request, 'UserScreen.html', context)

def getCount(name):
    count = 0
    for i in range(len(blockchain.chain)):
        if i > 0:
            b = blockchain.chain[i]
            data = b.transactions[0]
            arr = data.split("#")
            if arr[1] == name:
                count += 1
    return count

def ViewVotes(request):
    if request.method == 'GET':
        output = '<div class="container mt-4"><div class="table-responsive">'
        output += '<table class="table table-bordered table-striped text-center">'
        output += ('<thead class="thead-dark"><tr>'
                   '<th>Candidate Name</th>'
                   '<th>Party Name</th>'
                   '<th>Area Name</th>'
                   '<th>Image</th>'
                   '<th>Vote Count</th>'
                   '</tr></thead><tbody>')
        con = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', database='evoting', charset='utf8')
        with con:
            cur = con.cursor()
            cur.execute("select * FROM addparty")
            rows = cur.fetchall()
            for row in rows:
                cname = row[0]
                count = getCount(cname)
                pname = str(row[1])
                area = row[2]
                output += '<tr>'
                output += f'<td>{cname}</td>'
                output += f'<td>{pname}</td>'
                output += f'<td>{area}</td>'
                output += f'<td><img src="/static/parties/{cname}.png" class="img-fluid" style="max-width:200px;"></td>'
                output += f'<td>{str(count)}</td>'
                output += '</tr>'
        output += '</tbody></table></div></div>'
        context = {'data': output}
        return render(request, 'ViewVotes.html', context)

def ViewParty(request):
    if request.method == 'GET':
        output = '<div class="container mt-4"><div class="table-responsive">'
        output += '<table class="table table-bordered table-striped text-center">'
        output += ('<thead class="thead-dark"><tr>'
                   '<th>Candidate Name</th>'
                   '<th>Party Name</th>'
                   '<th>Area Name</th>'
                   '<th>Image</th>'
                   '</tr></thead><tbody>')
        con = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', database='evoting', charset='utf8')
        with con:
            cur = con.cursor()
            cur.execute("select * FROM addparty")
            rows = cur.fetchall()
            for row in rows:
                cname = row[0]
                pname = str(row[1])
                area = row[2]
                output += '<tr>'
                output += f'<td>{cname}</td>'
                output += f'<td>{pname}</td>'
                output += f'<td>{area}</td>'
                output += f'<td><img src="/static/parties/{cname}.png" class="img-fluid" style="max-width:200px;"></td>'
                output += '</tr>'
        output += '</tbody></table></div></div>'
        context = {'data': output}
        return render(request, 'ViewParty.html', context)

def AddPartyAction(request):
    if request.method == 'POST':
        cname = request.POST.get('t1', False)
        pname = request.POST.get('t2', False)
        area = request.POST.get('t3', False)
        myfile = request.FILES['t4']

        fs = FileSystemStorage()
        filename = fs.save('EVotingApp/static/parties/' + cname + '.png', myfile)
        
        db_connection = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', database='evoting', charset='utf8')
        db_cursor = db_connection.cursor()
        student_sql_query = "INSERT INTO addparty(candidatename,partyname,areaname,image) VALUES(%s, %s, %s, %s)"
        db_cursor.execute(student_sql_query, (cname, pname, area, cname))
        db_connection.commit()
        print(db_cursor.rowcount, "Record Inserted")
        if db_cursor.rowcount == 1:
            context = {'data': 'Party Details Added'}
            return render(request, 'AddParty.html', context)
        else:
            context = {'data': 'Error in adding party details'}
            return render(request, 'AddParty.html', context)

def saveSignup(request):
    if request.method == 'POST':
        global username, password, contact, email, address
        img = cv2.imread('EVotingApp/static/photo/test.png')
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face_component = None
        faces = face_detection.detectMultiScale(gray, 1.3, 5)
        for (x, y, w, h) in faces:
            face_component = img[y:y+h, x:x+w]
        if face_component is not None:
            cv2.imwrite('EVotingApp/static/profiles/' + username + '.png', face_component)
            db_connection = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', database='evoting', charset='utf8')
            db_cursor = db_connection.cursor()
            student_sql_query = "INSERT INTO register(username,password,contact,email,address) VALUES(%s, %s, %s, %s, %s)"
            db_cursor.execute(student_sql_query, (username, password, contact, email, address))
            db_connection.commit()
            print(db_cursor.rowcount, "Record Inserted")
            if db_cursor.rowcount == 1:
                context = {'data': 'Signup Process Completed'}
                return render(request, 'Register.html', context)
            else:
                context = {'data': 'Unable to detect face. Please retry'}
                return render(request, 'Register.html', context)

def Signup(request):
    if request.method == 'POST':
        global username, password, contact, email, address
        username = request.POST.get('username', False)
        password = request.POST.get('password', False)
        contact = request.POST.get('contact', False)
        email = request.POST.get('email', False)
        address = request.POST.get('address', False)
        context = {'data': 'Capture Your Face'}
        return render(request, 'CaptureFace.html', context)

def AdminLogin(request):
    if request.method == 'POST':
        global username
        username = request.POST.get('username', False)
        password = request.POST.get('password', False)
        if username == 'admin' and password == 'admin':
            context = {'data': 'Welcome ' + username}
            return render(request, 'AdminScreen.html', context)
        else:
            context = {'data': 'Invalid login details'}
            return render(request, 'Admin.html', context)

def getCurrentHour():
    now = datetime.now()
    dt = str(now)
    arr = dt.split(" ")
    arr = arr[1].strip().split(":")
    return int(arr[0])

def UserLogin(request):
    if request.method == 'POST':
        global email_id, username
        username = request.POST.get('username', False)
        password = request.POST.get('password', False)
        status = 'none'
        con = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', database='evoting', charset='utf8')
        with con:
            cur = con.cursor()
            cur.execute("select * FROM register")
            rows = cur.fetchall()
            for row in rows:
                if row[0] == username and row[1] == password:
                    email_id = row[3]
                    status = 'success'
                    break
        if status == 'success':
            hour = getCurrentHour()
            if hour >= 9 and hour < 18:
                with open('session.txt', 'w') as file:
                    file.write(username)
                context = {'data': f'<div class="container mt-4"><h3>Welcome {username}</h3></div>'}
                return render(request, 'UserScreen.html', context)
            else:
                context = {'data': 'Login & Voting will be allowed between 9:00 AM to 6:00 PM'}
                return render(request, 'Login.html', context)
        else:
            context = {'data': 'Invalid login details'}
            return render(request, 'Login.html', context)










# from django.shortcuts import render
# from django.template import RequestContext
# from django.contrib import messages
# import pymysql
# from django.http import HttpResponse
# from django.core.files.storage import FileSystemStorage
# import os
# from Blockchain import *
# from Block import *
# from datetime import date
# import cv2
# import numpy as np
# import base64
# import random
# from datetime import datetime
# from PIL import Image
# import smtplib 
# from email.message import EmailMessage
# from datetime import datetime



# global username, password, contact, address
# global classifier
# global email_id
# global otp

# blockchain = Blockchain()
# if os.path.exists('blockchain_contract.txt'):
#     with open('blockchain_contract.txt', 'rb') as fileinput:
#         blockchain = pickle.load(fileinput)
#     fileinput.close()

# face_detection = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
# recognizer = cv2.face_LBPHFaceRecognizer.create()

# def AddParty(request):
#     if request.method == 'GET':
#        return render(request, 'AddParty.html', {})

# def index(request):
#     if request.method == 'GET':
#        return render(request, 'index.html', {})

# def Login(request):
#     if request.method == 'GET':
#        return render(request, 'Login.html', {})

# def CastVote(request):
#     if request.method == 'GET':
#        return render(request, 'CastVote.html', {})
    

# def Register(request):
#     if request.method == 'GET':
#        return render(request, 'Register.html', {})

# def Admin(request):
#     if request.method == 'GET':
#        return render(request, 'Admin.html', {})
    
# def WebCam(request):
#     if request.method == 'GET':
#         data = str(request)
#         formats, imgstr = data.split(';base64,')
#         imgstr = imgstr[0:(len(imgstr)-2)]
#         data = base64.b64decode(imgstr)
#         if os.path.exists("EVotingApp/static/photo/test.png"):
#             os.remove("EVotingApp/static/photo/test.png")
#         with open('EVotingApp/static/photo/test.png', 'wb') as f:
#             f.write(data)
#         f.close()
#         context= {'data':"done"}
#         return HttpResponse("Image saved")    

# def checkUser(name):
#     flag = 0
#     for i in range(len(blockchain.chain)):
#           if i > 0:
#               b = blockchain.chain[i]
#               data = b.transactions[0]
#               print(data)
#               arr = data.split("#")
#               if arr[0] == name:
#                   flag = 1
#                   break
#     return flag            

# def getOutput(status):
#     output = '<h3><br/>'+status+'<br/><table border=1 align=center>'
#     output+='<tr><th><font size=3 color=black>Candidate Name</font></th>'
#     output+='<th><font size=3 color=black>Party Name</font></th>'
#     output+='<th><font size=3 color=black>Area Name</font></th>'
#     output+='<th><font size=3 color=black>Image</font></th>'
#     output+='<th><font size=3 color=black>Cast Vote Here</font></th></tr>'
#     con = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'evoting',charset='utf8')
#     with con:
#         cur = con.cursor()
#         cur.execute("select * FROM addparty")
#         rows = cur.fetchall()
#         for row in rows:
#             cname = row[0]
#             pname = str(row[1])
#             area = row[2]
#             image = row[3]
#             output+='<tr><td><font size=3 color=black>'+cname+'</font></td>'
#             output+='<td><font size=3 color=black>'+pname+'</font></td>'
#             output+='<td><font size=3 color=black>'+area+'</font></td>'
#             output+='<td><img src="/static/parties/'+cname+'.png" width=200 height=200></img></td>'
#             output+='<td><a href="FinishVote?id='+cname+'"><font size=3 color=black>Click Here</font></a></td></tr>'
#     output+="</table><br/><br/><br/><br/><br/><br/>"        
#     return output      

# def sendEmail():
#     global email_id
#     global otp
#     msg = EmailMessage()
#     msg.set_content("Your OTP is : "+str(otp))
#     msg['Subject'] = 'E-Voting OTP'
#     msg['From'] = "myprojectstp@gmail.com"
#     msg['To'] = email_id
#     print(email_id)
    
#     s = smtplib.SMTP('smtp.gmail.com', 587)
#     s.starttls()
#     s.login("myprojectstp@gmail.com", "paxgxdrhifmqcrzn")
#     s.send_message(msg)
#     s.quit()


# def FinishVote(request):
#     if request.method == 'GET':
#         global username
#         cname = request.GET.get('id', False)
#         voter = ''
#         today = date.today()
#         data = str(username)+"#"+str(cname)+"#"+str(today)
#         blockchain.add_new_transaction(data)
#         hash = blockchain.mine()
#         b = blockchain.chain[len(blockchain.chain)-1]
#         print("Previous Hash : "+str(b.previous_hash)+" Block No : "+str(b.index)+" Current Hash : "+str(b.hash))
#         bc = "Previous Hash : "+str(b.previous_hash)+"<br/>Block No : "+str(b.index)+"<br/>Current Hash : "+str(b.hash)
#         blockchain.save_object(blockchain,'blockchain_contract.txt')
#         context= {'data':'<font size=3 color=black>Your Vote Accepted<br/>'+bc}
#         return render(request, 'UserScreen.html', context)
    
# def getUserImages():
#     names = []
#     ids = []
#     faces = []
#     dataset = "EVotingApp/static/profiles"
#     count = 0
#     for root, dirs, directory in os.walk(dataset):
#         for j in range(len(directory)):
#             pilImage = Image.open(root+"/"+directory[j]).convert('L')
#             imageNp = np.array(pilImage,'uint8')
#             name = os.path.splitext(directory[j])[0]
#             names.append(name)
#             faces.append(imageNp)
#             ids.append(count)
#             count = count + 1
#     print(str(names)+" "+str(ids))        
#     return names, ids, faces        


# def getName(predict, ids, names):
#     name = "Unable to get name"
#     for i in range(len(ids)):
#         if ids[i] == predict:
#             name = names[i]
#             break
#     return name    

# def ValidateUser(request):
#     if request.method == 'POST':
#         global username
#         global otp
#         option = 0
#         status = "unable to predict user"
#         img = cv2.imread('EVotingApp/static/photo/test.png')
#         gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#         face_component = None
#         faces = face_detection.detectMultiScale(img,scaleFactor=1.1,minNeighbors=5,minSize=(30,30),flags=cv2.CASCADE_SCALE_IMAGE)
#         status = "Unable to predict.Please retry"
#         #for (x, y, w, h) in faces:
#         #    face_component = gray[y:y+h, x:x+w]
#         faces = sorted(faces, reverse=True,key=lambda x: (x[2] - x[0]) * (x[3] - x[1]))[0]
#         (fX, fY, fW, fH) = faces
#         face_component = gray[fY:fY + fH, fX:fX + fW]
#         if face_component is not None:
#             names, ids, faces = getUserImages()
#             recognizer.train(faces, np.asarray(ids))
#             predict, conf = recognizer.predict(face_component)
#             print(str(predict)+" === "+str(conf))
#             if(conf < 80):
#                 validate_user = getName(predict, ids, names)
#                 print(str(validate_user)+" "+str(username))
#                 if validate_user == username:
#                     status = "success"
#         else:
#             status = "Unable to detect face"
#         if status == "success":
#             flag = checkUser(username)
#             if flag == 0:
#                 option = 1
#         if option == 1:
#             otp = random.randint(1000,5000)
#             print(otp)
#             sendEmail()
#             context= {'data':"OTP sent to your mail"}
#             return render(request, 'OTPValidation.html', context)
#         else:
#             context= {'data':status}
#             return render(request, 'UserScreen.html', context)

# def OTPAction(request):
#     if request.method == 'POST':
#         global otp
#         otp_value = request.POST.get('t1', False)
#         if otp_value == str(otp):
#             output = getOutput('OTP Validation Successfull')
#             context= {'data':output}
#             return render(request, 'VotePage.html', context)
#         else:
#             context= {'data':'Invalid OTP'}
#             return render(request, 'UserScreen.html', context)
        

# def getCount(name):
#     count = 0
#     for i in range(len(blockchain.chain)):
#           if i > 0:
#               b = blockchain.chain[i]
#               data = b.transactions[0]
#               arr = data.split("#")
#               if arr[1] == name:
#                   count = count + 1
                  
#     return count

# def ViewVotes(request):
#     if request.method == 'GET':
#         output = '<table border=1 align=center>'
#         output+='<tr><th><font size=3 color=black>Candidate Name</font></th>'
#         output+='<th><font size=3 color=black>Party Name</font></th>'
#         output+='<th><font size=3 color=black>Area Name</font></th>'
#         output+='<th><font size=3 color=black>Image</font></th>'
#         output+='<th><font size=3 color=black>Vote Count</font></th>'
#         con = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'evoting',charset='utf8')
#         with con:
#             cur = con.cursor()
#             cur.execute("select * FROM addparty")
#             rows = cur.fetchall()
#             for row in rows:
#                 cname = row[0]
#                 count = getCount(cname)
#                 pname = str(row[1])
#                 area = row[2]
#                 image = row[3]
#                 output+='<tr><td><font size=3 color=black>'+cname+'</font></td>'
#                 output+='<td><font size=3 color=black>'+pname+'</font></td>'
#                 output+='<td><font size=3 color=black>'+area+'</font></td>'
#                 output+='<td><img src="/static/parties/'+cname+'.png" width=200 height=200></img></td>'
#                 output+='<td><font size=3 color=black>'+str(count)+'</font></td></tr>'
#         output+="</table><br/><br/><br/><br/><br/><br/>"        
#         context= {'data':output}
#         return render(request, 'ViewVotes.html', context)    
            
# def ViewParty(request):
#     if request.method == 'GET':
#         output = '<table border=1 align=center>'
#         output+='<tr><th><font size=3 color=black>Candidate Name</font></th>'
#         output+='<th><font size=3 color=black>Party Name</font></th>'
#         output+='<th><font size=3 color=black>Area Name</font></th>'
#         output+='<th><font size=3 color=black>Image</font></th>'
#         con = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'evoting',charset='utf8')
#         with con:
#             cur = con.cursor()
#             cur.execute("select * FROM addparty")
#             rows = cur.fetchall()
#             for row in rows:
#                 cname = row[0]
#                 pname = str(row[1])
#                 area = row[2]
#                 image = row[3]
#                 output+='<tr><td><font size=3 color=black>'+cname+'</font></td>'
#                 output+='<td><font size=3 color=black>'+pname+'</font></td>'
#                 output+='<td><font size=3 color=black>'+area+'</font></td>'
#                 output+='<td><img src="/static/parties/'+cname+'.png" width=200 height=200></img></td></tr>'
#         output+="</table><br/><br/><br/><br/><br/><br/>"        
#         context= {'data':output}
#         return render(request, 'ViewParty.html', context)    

# def AddPartyAction(request):
#     if request.method == 'POST':
#       cname = request.POST.get('t1', False)
#       pname = request.POST.get('t2', False)
#       area = request.POST.get('t3', False)
#       myfile = request.FILES['t4']

#       fs = FileSystemStorage()
#       filename = fs.save('EVotingApp/static/parties/'+cname+'.png', myfile)
      
#       db_connection = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'evoting',charset='utf8')
#       db_cursor = db_connection.cursor()
#       student_sql_query = "INSERT INTO addparty(candidatename,partyname,areaname,image) VALUES('"+cname+"','"+pname+"','"+area+"','"+cname+"')"
#       db_cursor.execute(student_sql_query)
#       db_connection.commit()
#       print(db_cursor.rowcount, "Record Inserted")
#       if db_cursor.rowcount == 1:
#        context= {'data':'Party Details Added'}
#        return render(request, 'AddParty.html', context)
#       else:
#        context= {'data':'Error in adding party details'}
#        return render(request, 'AddParty.html', context)    

# def saveSignup(request):
#     if request.method == 'POST':
#         global username, password, contact, email, address
#         img = cv2.imread('EVotingApp/static/photo/test.png')
#         gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#         face_component = None
#         faces = face_detection.detectMultiScale(gray, 1.3,5)
#         for (x, y, w, h) in faces:
#             face_component = img[y:y+h, x:x+w]
#         if face_component is not None:
#             cv2.imwrite('EVotingApp/static/profiles/'+username+'.png',face_component)
#             db_connection = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'evoting',charset='utf8')
#             db_cursor = db_connection.cursor()
#             student_sql_query = "INSERT INTO register(username,password,contact,email,address) VALUES('"+username+"','"+password+"','"+contact+"','"+email+"','"+address+"')"
#             db_cursor.execute(student_sql_query)
#             db_connection.commit()
#             print(db_cursor.rowcount, "Record Inserted")
#             if db_cursor.rowcount == 1:
#                 context= {'data':'Signup Process Completed'}
#                 return render(request, 'Register.html', context)
#             else:
#                 context= {'data':'Unable to detect face. Please retry'}
#                 return render(request, 'Register.html', context)


# def Signup(request):
#     if request.method == 'POST':
#       global username, password, contact, email, address
#       username = request.POST.get('username', False)
#       password = request.POST.get('password', False)
#       contact = request.POST.get('contact', False)
#       email = request.POST.get('email', False)
#       address = request.POST.get('address', False)
#       context= {'data':'Capture Your face'}
#       return render(request, 'CaptureFace.html', context)
      
# def AdminLogin(request):
#     if request.method == 'POST':
#         global username
#         username = request.POST.get('username', False)
#         password = request.POST.get('password', False)
#         if username == 'admin' and password == 'admin':
#             context= {'data':'Welcome '+username}
#             return render(request, 'AdminScreen.html', context)
#         if status == 'none':
#             context= {'data':'Invalid login details'}
#             return render(request, 'Admin.html', context)

# def getCurrentHour():
#     now = datetime.now()
#     dt = str(now)
#     arr = dt.split(" ")
#     arr = arr[1].strip().split(":")
#     return int(arr[0])

# def UserLogin(request):
#     if request.method == 'POST':
#         global email_id, username
#         username = request.POST.get('username', False)
#         password = request.POST.get('password', False)
#         status = 'none'
#         con = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'evoting',charset='utf8')
#         with con:
#             cur = con.cursor()
#             cur.execute("select * FROM register")
#             rows = cur.fetchall()
#             for row in rows:
#                 if row[0] == username and row[1] == password:
#                     email_id = row[3]
#                     status = 'success'
#                     break
#         if status == 'success':
#             hour = getCurrentHour()
#             if hour >= 9 and hour < 18:
#                 file = open('session.txt','w')
#                 file.write(username)
#                 file.close()
#                 context= {'data':'<center><font size="3" color="black">Welcome '+username+'<br/><br/><br/><br/><br/>'}
#                 return render(request, 'UserScreen.html', context)
#             else:
#                 context= {'data':'Login & Voting will be allowed between 9:00 AM to 6:00 PM'}
#                 return render(request, 'Login.html', context)
#         if status == 'none':
#             context= {'data':'Invalid login details'}
#             return render(request, 'Login.html', context)





        
            
