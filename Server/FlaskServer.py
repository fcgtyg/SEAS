# -*- coding:UTF-8 -*-

from flask import Flask, request, jsonify
from Models.MySQLdb import MySQLdb
from Models.Password import Password
from Models.Credential import Credential
from Models.Question import Question
from Models.Exam import Exam
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity, get_raw_jwt
import json
import datetime
import pickle

app = Flask(__name__)
db = MySQLdb("TestDB", app)
app.config["DEBUG"] = True
app.config["UPLOAD_FOLDER"] = "./uploads/"
app.config["JWT_SECRET_KEY"] = "CHANGE THIS BEFORE DEPLOYMENT ! ! !"
app.config["JWT_BLACKLIST_ENABLED"] = True
app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access', 'refresh']
if app.config["DEBUG"]:
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False
else:
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(hours=18)

jwt = JWTManager(app)
expired_token = set()

def check_auth(token, allowed_organization, min_allowed_role):
    role_ranks = {
        "student": ["superuser", "admin", "lecturer", "student"],
        "lecturer": ["superuser", "admin", "lecturer"],
        "admin": ["superuser", "admin"],
        "superuser": ["superuser"]
                  }

    allowed_roles = role_ranks[min_allowed_role]
    user, role, token_time, organization = token
    return role in allowed_roles and organization == allowed_organization

@app.route("/")
def test_connection():
    return jsonify("I am alive!")


@app.route("/organizations", methods=["PUT"])
@jwt_required
def signUpOrganization():
    if check_auth(get_jwt_identity(), "main", "superuser"):
        return jsonify(db.initialize_organization(request.form["data"]))
    else:
        return jsonify("Unauthorized access!")


@app.route("/organizations/<string:organization>", methods = ["PUT"])
@jwt_required
def signUpUser(organization):
    token = get_jwt_identity()
    if not check_auth(token, organization ,"admin"):
        return jsonify("Unauthorized access!")
    else:
        passwd = Password().hashPassword(request.form["Password"])
        username = request.form["Username"]
        role = request.form["Role"].lower()
        command = "Insert into %s.members(PersonID, Role, Name, Surname, Username, Password, Email, Department) " \
                  "values(%s, '%d', '%s', '%s', '%s', '%s', '%s', '%s')" \
                  % (organization,
                     request.form["ID"],
                     int(db.execute("SELECT RoleID FROM %s.roles WHERE Role = '%s'" % (
                     organization, role))[0][0]),
                     request.form["Name"],
                     request.form["Surname"],
                     username,
                     passwd,
                     request.form["Email"],
                     request.form["Department"]
                     )

        rtn = jsonify(db.execute(command))
        return rtn


@app.route("/organizations/<string:organization>/<string:username>", methods=["GET"])
# todo: Fatihgulmez , separate data manipulation and access from views!!!
def signInUser(organization, username):
    organization = organization.replace(" ", "_").lower()
    username = request.authorization["username"]
    try:
        passwd = db.execute("select Password from %s.members where Username = '%s'"
                            % (organization, username))[0][0]
        if Password().verify_password_hash(request.authorization["password"], passwd):
            rtn = list(db.execute("select Username, Name, Surname, PersonID, Role, Email, Department "
                                  "from %s.members where Username=('%s')" % (organization, username))[0])
            rtn[4] = db.execute("SELECT Role FROM %s.roles WHERE RoleID = '%s'" % (organization, rtn[4]))[0][0]
            rtn.append(organization)
            token = create_access_token(identity=(rtn[0], rtn[4], str(datetime.datetime.today()), rtn[7]))
            rtn.append(token)
            return jsonify(rtn)

        else:
            return jsonify("Wrong Password")
    except IndexError:
        return jsonify("Wrong Username")


@app.route("/organizations/<string:organization>/<string:username>/out", methods=["PUT"])
@jwt_required
def signOutUser(organization, username):
    identity = get_jwt_identity()
    if username != identity[0] or organization != identity[3]:
        return jsonify("Unauthorized access!")
    token = get_raw_jwt()["jti"]
    return jsonify({"Log out status": db.revoke_token(token) is not None})


@jwt.token_in_blacklist_loader
def is_revoked(token):
    jti = token["jti"]
    return db.if_token_revoked(jti)


@app.route("/organizations/<string:organization>/<string:course>", methods=['PUT'])
@jwt_required
def addCourse(organization, course):
    token = get_jwt_identity()
    if not check_auth(token, organization, "admin"):
        return jsonify("Unauthorized access!")
    else:
        name = request.form["name"]
        code = request.form["code"]
        lecturers = request.form["lecturers"]
        return jsonify(db.add_course(organization, name, code, lecturers))


@app.route("/organizations/<string:organization>/<string:course>/get", methods=['GET'])
@jwt_required
def getCourse(organization, course):
    if not check_auth(get_jwt_identity(), organization, "student"):
        return jsonify("Unauthorized Access.")
    return jsonify(db.get_course(organization, course))


@app.route("/organizations/<string:organization>/<string:course>/register/<string:liste>", methods=['PUT'])
@jwt_required
def putStudentList(organization, course, liste):
    token = get_jwt_identity()
    if not check_auth(token, organization, "lecturer"):
        return jsonify("Unauthorized access!")
    else:
        return jsonify(db.registerStudentCSV(request.files["liste"], organization, course, request.form["username"]))


@app.route("/organizations/<string:organization>/<string:course>/register", methods=['GET'])
@jwt_required
def getStudentList(organization, course):
    token = get_jwt_identity()
    if not check_auth(token, organization, "lecturer"):
        return jsonify("Unauthorized access!")
    return jsonify(db.get_course_participants(course, organization))


@app.route("/organizations/<string:organization>/<string:username>/courses/role=lecturer", methods=["GET"])
@jwt_required
def getLecturerCourseList(organization, username):
    token = get_jwt_identity()
    if not check_auth(token, organization, "lecturer"):
        return jsonify(db.get_student_courses(organization, username))
    else:
        return jsonify(db.get_lecturer_courses(organization, username))


@app.route("/organizations/<string:organization>/<string:course>/delete_user", methods=['DELETE'])
@jwt_required
def deleteStudentFromLecture(organization, course):
    token = get_jwt_identity()
    if not check_auth(token, organization, "lecturer"):
        return jsonify("Unauthorized access!")
    else:
        return jsonify(db.delete_student_course(organization, course, request.form["Student"]))


@app.route("/organizations/<string:organization>/<string:username>/edit_password", methods=["PUT"])
@jwt_required
def changePassword(organization, username):
    user, role, tokentime, organization_auth = get_jwt_identity()
    if username != user or organization_auth != organization:
        return jsonify("Unauthorized access!")
    ismail = request.form["isMail"]
    if ismail == "True":
        ismail = True
    else:
        ismail = False
    return jsonify(db.changePasswordOREmail(organization, user, request.form["Password"], request.form["newPassword"], email=ismail))


@app.route("/organizations/<string:organization>/<string:course>/exams/add", methods=["PUT"])
@jwt_required
def addExam(organization, course):
    token = get_jwt_identity()
    if not check_auth(token, organization, "lecturer"):
        return jsonify("Unauthorized access!")
    else:
        name = request.form["name"]
        time = request.form["time"]
        duration = request.form["duration"]
        questions = json.loads(request.form["questions"])
        status = request.form["status"]
        exam = Exam(name, organization, db)
        exam.save(course, time, duration, status)
        exam.get()
        for j in questions:
            i=questions[j]
            exam.addQuestion(
                i["type"],
                i["subject"],
                i["text"],
                i["answer"],
                i["inputs"],
                i["outputs"],
                i["value"],
                i["tags"])
        return jsonify(exam.save(course, time, duration, status))


@app.route("/organizations/<string:organization>/<string:course>/exams/<string:exam>/delete", methods=["DELETE"])
@jwt_required
def deleteExam(organization, course, exam):
    token = get_jwt_identity()
    if not check_auth(token, organization, "lecturer"):
        return jsonify("Unauthorized access!")
    else:
        return jsonify(Exam(exam, organization, db).delete_exam())


@app.route("/organizations/<string:organization>/<string:course>/exams/", methods=["GET"])
@jwt_required
# todo: STUDENT CANNOT REACH QUESTIONS BEFORE EXAM START TIME
def getExamsOfLecture(organization, course):
    token = get_jwt_identity()
    if not check_auth(token, organization, "student"):
        return jsonify("Unauthorized access!")
    return jsonify(db.get_exams_of_lecture(organization, course))


@app.route("/organizations/<string:organization>/<string:course>/exams/<string:name>", methods=["GET"])
@jwt_required
def getExam(organization, course, name):
    token = get_jwt_identity()
    if not check_auth(token, organization, "student"):
        return jsonify("Unauthorized access!")
    exam = Exam(name, organization, db)
    return jsonify(exam.get())


@app.route("/organizations/<string:organization>/<string:course>/exams/<string:name>/addQuestion", methods=["PUT"])
@jwt_required
def addQuestionsToExam(organization, course, name):
    token = get_jwt_identity()
    if not check_auth(token, "lecturer"):
        return jsonify("Unauthorized access!")
    else:
        info = json.loads(request.form["data"])
        rtn = Exam(name, organization, db=db).addQuestion(info["type"], info["subject"], info["text"], info["answer"], info["inputs"], info["outputs"], info["value"], info["tags"])
        return jsonify(rtn)


@app.route("/organizations/<string:organization>/<string:course>/exams/<question_id>/answers/<string:username>", methods=["PUT"])
@jwt_required
def answerExam(organization, course, question_id, username):
    token = get_jwt_identity()
    if token[1] != "student":
        return jsonify("Unauthorized access!")
    return jsonify(db.add_answer(organization, question_id, username, request.form["answers"]))


@app.route("/organizations/<string:organization>/<string:username>/pic", methods=["PUT", "GET"])
@jwt_required
def profilePicture(organization, username):
    token = get_jwt_identity()
    user = token[0]
    orga = token[3]
    if user != username and orga != organization:
        return jsonify("Unauthorized access!")
    if request.method == "PUT":
        user, role, tokentime = get_jwt_identity()
        pic = request.files["pic"]
        cont = request.form["pic"]
        if pic.filename == "":
            return jsonify("No picture selected.")
        return jsonify(db.upload_profile_pic(organization, user, pic, pickle.loads(cont), app.config["UPLOAD_FOLDER"]))
    else:
        path = db.get_profile_picture(organization, username)
        with open(path, "rb") as f:
            a = f.read()
        return jsonify(pickle.dumps(a))


@app.route("/organizations/<string:organization>/<string:course>/exams/<question_id>/answers/<string:studentUser>/grade", methods=["PUT"])
@jwt_required
def gradeQuestion(organization, course, question_id, studentUser):
    user, role, tokentime, organization_auth = get_jwt_identity()
    if not check_auth(get_jwt_identity(), organization, "lecturer"):
        return "Unauthorized Access"
    else:
        return jsonify(db.grade_answer(organization, user, studentUser, question_id, request.form["grade"]))


@app.route("/organizations/<string:organization>/<string:course>/exams/<string:exam_name>/<string:question_id>/edit", methods=["PUT"])
@jwt_required
def editQuestion(organization, course, exam_name, question_id):
    user, role, token_time, organization = get_jwt_identity()
    if role != "lecturer":
        return jsonify("Unauthorized access!")
    return jsonify(Exam(exam_name, organization, db).edit_a_question(question_id, json.loads(request.form["data"])))


@app.route("/organizations/<string:organization>/<string:course>/exams/<string:exam_name>/more_time", methods=["PUT"])
@jwt_required
def addTimeToExam(organization, course, exam_name):
    user, role, token_time, organization = get_jwt_identity()
    if role != "lecturer":
        return jsonify("Unauthorized access!")
    return jsonify(Exam(exam_name, organization, db).add_more_time(request.form["additional_time"]))


@app.route("/organizations/<string:organization>/<string:course>/exams/<string:exam_name>/status", methods=["PUT"])
@jwt_required
def changeStatusOfExam(organization, course, exam_name):
    user, role, token_time, organization = get_jwt_identity()
    if role != "lecturer":
        return jsonify("Unauthorized access!")
    return jsonify(Exam(exam_name, organization, db).change_status(request.form["status"]))


@app.route("/organizations/<string:organization>/<string:username>/reset_password", methods=["GET", "PUT"])
def reset_password(organization, username):
    if request.method == "GET":
        # send an e mail with generated password.
        return jsonify(db.resetPassword(organization, username))
    else:
        # accept the generated pass and new one and change password.
        return  jsonify(db.checkAndChangePassword(organization, username, request.authorization["username"], new_pass=request.authorization["password"]))


if __name__ == "__main__":
    app.run(host="localhost", port=8888, threaded=True)
