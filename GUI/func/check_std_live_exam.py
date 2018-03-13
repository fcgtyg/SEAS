import sys
sys.path.append("../..")

from GUI.func import database_api

def check_std_live_exam(self, dt):
    try:
        # self.data_live_exam = database_api...

        if self.data_live_exam is not None:
            self.ids["btn_join_exam"].disabled = False
            self.ids["txt_join_exam_name"].color = (1,1,1,1)
            self.ids["txt_join_exam_name"].text = "%s has started!" % self.data_live_exam
        else:
            self.ids["btn_join_exam"].disabled = True
            self.ids["txt_join_exam_name"].color = (1,1,1,0.25)
            self.ids["txt_join_exam_name"].text = "No exam started"
    except:
        print ("SEAS [ERROR]: check_std_live_exam > Except > Server Connection Not Found")