import sys
sys.path.append("../..")

from GUI.func import database_api

def check_connection(img, dt):
    try:
        if database_api.testConnection():
            img.source = "img/ico_connection_success.png"
        else:
            img.source = "img/ico_connection_fail.png"
            print ("SEAS [ERROR]: check_connection > Try > Server Connection Failed")
    except:
        img.source = "img/ico_connection_fail.png"
        print ("SEAS [ERROR]: check_connection > Except > Server Connection Not Found")
    finally:
        img.reload()