#!/usr/bin/python
# -*- coding: utf-8 -*-
# $Id: rd_main.pyw 2221 2009-08-14 17:00:29Z gallag $

#Standard Modules
import sys, os
import time, datetime
import lxml.etree
import itertools
import pdb
import string

# This is for the GUI
from PyQt4 import QtCore, QtGui, uic
import res

# General Variables
parent_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
sys.path.append(parent_dir)         # This is to read from the parent directory
VERSION = '0.1 Beta'

# QT Configuration
QtCore.pyqtRemoveInputHook()
mui_path = os.path.join(os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), 'ui_forms'), 'mainui.ui')

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Main(QtGui.QMainWindow):
    def __init__(self):
        # Initiate the UI (Python code)
        self.app = QtGui.QApplication(sys.argv)
        QtGui.QMainWindow.__init__(self)
        uic.loadUi(mui_path, self)
        self.connect(self.actionClose_without_Save, QtCore.SIGNAL('triggered()'), self.closeEvent)
        self.font_size = 10

        ##GET Instance##
        self.app = self.app.instance()
        
        #Create Timer
        self.myTimer = QtCore.QTimer()
        QtCore.QObject.connect(self.myTimer,QtCore.SIGNAL("timeout()"), self.updateTimer)

        #Load the constants and defaults
        self.loadconst()      
        self.loadxml()
        self.loadDefaults()       
        # Most signals are already setup
        self.setupSignals()
    
    def loadxml(self):
        # xml File
        self.xml_path = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), 'timer_detail.xml')
        self.xml_data = lxml.etree.parse(self.xml_path)
        self.logfile = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), 'stg_time_2012.log')
        self.log_out = open(self.logfile,"a")      
    
    def loadconst(self):
        #a few constants
        self.timerTime = 0
        self.add_secs = 0
        self.log_start_time = ""
        self.log_restart_time =[]
        self.log_pause_time = []
        self.log_middle_time = ""
        self.log_end_time = ""
        self.wk_clock_boxes = [self.timeEdit_mon, self.timeEdit_tue, self.timeEdit_wed, self.timeEdit_thur, self.timeEdit_fri, self.timeEdit_wkend]
        self.wk_ot_boxes = [self.timeEdit_ot_mon, self.timeEdit_ot_tue, self.timeEdit_ot_wed, self.timeEdit_ot_thur, self.timeEdit_ot_fri, self.timeEdit_ot_wkend]
        self.xml_slot_pairs = [
            ("impdates/date1",      self.dateEdit_important_1  ),
            ("impdates/date2",      self.dateEdit_important_2  ),
            ("impdates/date3",      self.dateEdit_important_3  ),
            ("weekly/subtract",     self.timeEdit_subtract     ),
            ("weekly/clock/time1",  self.timeEdit_mon          ),
            ("weekly/clock/time2",  self.timeEdit_tue          ),
            ("weekly/clock/time3",  self.timeEdit_wed          ),
            ("weekly/clock/time4",  self.timeEdit_thur         ),
            ("weekly/clock/time5",  self.timeEdit_fri          ),
            ("weekly/clock/time6",  self.timeEdit_wkend        ),
            ("weekly/ots/ot1",      self.timeEdit_ot_mon       ),
            ("weekly/ots/ot2",      self.timeEdit_ot_tue       ),
            ("weekly/ots/ot3",      self.timeEdit_ot_wed       ),
            ("weekly/ots/ot4",      self.timeEdit_ot_thur      ),
            ("weekly/ots/ot5",      self.timeEdit_ot_fri       ),
            ("weekly/ots/ot6",      self.timeEdit_ot_wkend     ),
            ("weekly/progress",     self.timeEdit_progress     )
        ]
 
    def closeEvent(self, event=None):
        # Ask for permission to close
        reply = QtGui.QMessageBox.question(self, 'Message', "Are you sure you want to quit?", QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.Yes)
        if reply == QtGui.QMessageBox.Yes:
            if event: event.accept()
            QtGui.QApplication.instance().quit()
            sys.exit()
        else:
            if event: event.ignore()   
    
    def setupSignals(self):        
        # Menu Signals #
        # add save and add log
        for action, function in [
            (self.actionRecalculate, self.calculate),
            (self.actionReset_without_Save, self.reset_timer),
            (self.actionSaveAndClose, self.saveAndClose),
            (self.actionUpload_Time_Monday, self.uploadTime),
            (self.actionSave, self.saveDefaults),
            (self.actionWeekly_Goal, lambda: self.setGoal("Weekly Hours Goal", self.label_wk_goal, "weekly/goal" )),
            (self.actionGoal, lambda: self.setGoal("Yearly Hours Goal", self.label_goal, "yearly/goal")),
            (self.actionBillable_Hours, lambda: self.setGoal("Billable Hours", self.label_billable, "yearly/bill")),
            (self.actionNon_Discount_Hours, lambda: self.setGoal("Additional Non-Discounted Hours", self.label_nondiscount, "yearly/nondisc")),
            (self.actionDays_Off, lambda: self.setGoal("Vacation Days", self.label_time_off, "yearly/daysoff"))
            ]:
            self.connect(action, QtCore.SIGNAL('triggered()'), function)
        
        # Button Signals #
        self.connect(self.pushButton_start_pause, QtCore.SIGNAL('pressed()'), self.start_timer)
        self.connect(self.pushButton_save, QtCore.SIGNAL('pressed()'), self.save_timer)        
        self.pushButton_start_pause.setText("START")
        self.pushButton_save.setText("SAVE")
        self.pushButton_save.setEnabled(False)
        for xml_element, ui_box in self.xml_slot_pairs: self.connect(ui_box, QtCore.SIGNAL('editingFinished()'), lambda u=ui_box, e=xml_element: self.getlink(u, e))
 
    def saveAndClose(self):
        # Save on close
        self.saveDefaults()
        self.closeEvent()
         
    def getlink(self, u, e):
        #Update the xml, ui, and run calculations
        setattr(self.xml_data.find(e), 'text', str(u.text()))
        self.calculate()

    def loadDefaults(self):
        # Convenience function that sets commonly used variables based on the current times. 
        self.timer = int(self.xml_data.find('timer').text)
        self.prev_timer = int(self.xml_data.find('prev_timer').text)        
        self.yearly = {}
       
        for child in self.xml_data.findall("yearly/*"): self.yearly[child.tag]=child.text

        self.weekly_clock = [child.text for child in self.xml_data.findall("weekly/clock/*")]
        self.weekly_ot = [child.text for child in self.xml_data.findall("weekly/ots/*")]        
        self.impdays = [child.text for child in self.xml_data.findall("impdates/*")]
        #Loads values into UI
        self.updateUI()

    def updateUI(self):
        # Timer
        self.label_timer.setText(str(datetime.timedelta(seconds=(self.timer))))

        # Yearly
        yearly={"bill":self.label_billable, "total":self.label_currentTotal, "goal":self.label_goal, "need":self.label_needed, "nondisc":self.label_nondiscount, "daysoff":self.label_time_off}
        for label in self.yearly: yearly[label].setText(self.yearly[label])

        # Weekly
        self.label_wk_goal.setText(self.xml_data.find("weekly/goal").text)
        self.updateTime(self.timeEdit_subtract, self.xml_data.find('weekly/subtract').text)
        self.updateTime(self.timeEdit_progress, self.xml_data.find('weekly/progress').text)
        
        for x,y in zip(self.wk_clock_boxes, self.weekly_clock): self.updateTime(x,y, True)
        for x,y in zip(self.wk_ot_boxes, self.weekly_ot): self.updateTime(x,y, True)
        
        # Important Dates 
        for (x,y) in zip([self.dateEdit_important_1, self.dateEdit_important_2, self.dateEdit_important_3], self.impdays): self.updateTime(x,y, True)
        self.label_timer.setText( str(datetime.timedelta(seconds=(self.timer))) )
        
        #Calculate all the new data
        self.calculate()
        
    def setGoal(self, name, label, xml_tag):
        #Create a new goal and update all the calculations
        new_amt, ok = QtGui.QInputDialog.getText(self, 'Update Details', 'New Amount for: "%s":' %name)
        new_amt = str(new_amt)
        if not ok:
            # User Canceled
            return
        else: 
            #Verify a good number
            try: new_amt = str(int(round(float(new_amt),0)))
            except:
                QtGui.QMessageBox.information(None, "Try Again", "%s is not a valid number for %s, please try again"%(new_amt, name), "OK")
                return
            #Fix non-discounted hours to remove from standard billable time
            if name == "Additional Non-Discounted Hours": 
                self.yearly['bill'] = str(int(self.label_billable.text())-int(new_amt))
                self.label_billable.setText(self.yearly['bill'])
                self.xml_data.find("yearly/bill").text = self.yearly['bill']
                new_amt = str( int(new_amt) + int(self.label_nondiscount.text() ) )
            label.setText(new_amt)
            self.xml_data.find(xml_tag).text = new_amt
            if "yearly" in xml_tag: self.yearly[str(xml_tag.split("/")[1])] = new_amt
            self.updateUI()
        
    def calculate(self, reset=False):#
        # Calculates all the UI data

        # Calculate weekly Time
        tot_min =0
        for x in self.wk_clock_boxes: 
            tot_min += x.time().minute()
            tot_min += x.time().hour()*60
        for x in self.wk_ot_boxes: 
            tot_min += x.time().minute()
            tot_min += x.time().hour()*60
        self.clock_sec = tot_min *60
        self.label_time_clock.setText("%02d:%02d:00"%(tot_min/60, tot_min%60))
        # zip labels with weekly_ot and weekly_clock
        sub_secs = (self.timeEdit_subtract.time().hour()*3600)+(self.timeEdit_subtract.time().minute()*60)
        self.add_secs = (self.timeEdit_progress.time().hour()*3600)+(self.timeEdit_progress.time().minute()*60)

        self.wk_total = self.clock_sec + self.timer - sub_secs + self.add_secs

        # Weekly Time needed
        if (int(self.label_wk_goal.text())*3600) < self.wk_total: self.label_time_needed.setText("GOAL MET")
        else: self.label_time_needed.setText(str(datetime.timedelta(seconds=((int(self.label_wk_goal.text())*3600)-self.wk_total))))
        # Applicable OT
        self.label_ot.setText("%02d:%02d:00"%((40-(self.wk_total//3600))*-1,(self.wk_total%3600)//60))   
        # Show current total
        self.label_currentTotal.setText( str(int( (self.wk_total//3600) + int(self.label_billable.text())*.9 + int(self.label_nondiscount.text()))))
        # Yearly Goal
        self.label_needed.setText(str(int(self.yearly['goal'])-int(self.label_currentTotal.text())))

        # Special Goal Dates
        for dt, remaining_lbl, over_under_lbl in [(self.dateEdit_important_1.date(), self.label_time_remaining_1, self.label_time_over_under_1) ,(self.dateEdit_important_2.date(), self.label_time_remaining_2, self.label_time_over_under_2), (self.dateEdit_important_3.date(), self.label_time_remaining_3, self.label_time_over_under_3) ]:
            ct_wk = QtCore.QDate.currentDate().weekNumber()[0]
            pn_wk = dt.weekNumber()[0]
            weeks_left = (pn_wk)-(ct_wk)-(int(self.label_time_off.text())/5)
            total_weeks_left = 52 - ct_wk - (int(self.label_time_off.text())/5)
            planned = int(int(self.label_wk_goal.text())*.9)*(weeks_left)
            goal_remaining = int(self.yearly['goal']) - int(self.label_currentTotal.text() )
            remaining_lbl.setText(str(planned))
            over_under_lbl.setText(str(planned - (goal_remaining / total_weeks_left)*weeks_left ))

        # Now create monday upload time show
        self.uploadTime(reset)
        
    def uploadTime(self, reset=True):
        #This function would display the correct uploading time (minus monday am) and reset the timer as well as update the billable hours (time clock + timer - subtract) - 2.5 hours (extra clock / billable)
        wk_total = self.wk_total
        if reset: 
            #Ask about calculations and make sure you want to reset the timer
            reply = QtGui.QMessageBox.question(self, 'Message', "Are you sure you want to reset and save?", "Yes, I Have AM Time", "Yes, Without AM Time", "No")
            if reply == 0 :
                save_timer = int(self.timer) - int(self.prev_timer) + self.add_secs
                self.timer = int(self.prev_timer)
            elif reply == 1 : 
                save_timer = self.timer + self.add_secs
                self.timer = 0
            else: return
            if self.add_secs>0: self.log_time("Additional Weekly Time\t%02d:%02d:%02d"%(self.timeEdit_progress.time().hour(),self.timeEdit_progress.time().minute(),self.timeEdit_progress.time().second()))
            
            #Update the hours
            self.label_currentTotal.setText( str( int(self.yearly['bill']) + save_timer//3600 + self.clock_sec//3600 - 1 ))
            self.yearly['bill'] = str ( int(self.yearly['bill']) + save_timer//3600 + self.clock_sec//3600 - 1 )
            self.xml_data.find("yearly/bill").text = self.yearly['bill']
            self.xml_data.find("timer").text = str(self.timer)
            # Reset the timers and recalculate
            self.weekly_clock = ["08:00:00","08:00:00","08:00:00","08:00:00","08:00:00","00:00:00"]
            self.weekly_ot = ["00:00:00","00:00:00","00:00:00","00:00:00","00:00:00","00:00:00"]
            self.xml_data.find("weekly/subtract").text = "00:00:00"
            self.xml_data.find("weekly/progress").text = "00:00:00"
            self.updateUI()
            for xml_element, ui_box in self.xml_slot_pairs: self.xml_data.find(xml_element).text = str(ui_box.text())
        else: save_timer = self.timer + self.add_secs
        # Update the Monday Calculations
        if save_timer > (3600*8):
            #if greater than 8 hours we will need to divide between days
            wk_clock_end = self.updateTime( self.timeEdit_end_1, 3600*9 + 3600*8 )
            wk_clock_end2= self.updateTime( self.timeEdit_end_2, save_timer + 3600 )
            #Add update for labelWeeklyTotal
        else:
            wk_clock_end = self.updateTime( self.timeEdit_end_1 , save_timer + 3600*9 )
            wk_clock_end2= self.updateTime( self.timeEdit_end_2, 3600*9 )            
        self.labelWeeklyTotal.setText("%02d:%02d:00"%(((wk_total//3600)),(wk_total%3600)//60))

        self.updateTime(self.timeEdit_total, save_timer)
        
    def saveDefaults(self):
        # Save the current numbers to default xml
        self.xml_data.find('main/saved_date').text=str(time.strftime("%B %d, %Y", time.localtime(time.time())))
        xml_out = open(self.xml_path, "w")
        xml_out.write(lxml.etree.tostring(self.xml_data, pretty_print=True))
        
    def start_timer(self):
        # timer start or pause
        if self.pushButton_start_pause.text() == "PAUSE":
            self.pushButton_start_pause.setText("RESTART")
            self.pushButton_save.setText("SAVE")
            self.stop_timer()
        else:
            startTime = time.localtime(time.time())
            
            if self.pushButton_start_pause.text() == "RESTART":
                self.log_restart_time.append(time.strftime(" %I:%M:%S", time.localtime(time.time())))
            else: 
                self.log_start_time=time.strftime("%I:%M:%S", time.localtime(time.time()))
            self.pushButton_start_pause.setText("PAUSE")
            self.pushButton_save.setText("STOP AND SAVE")
            self.pushButton_save.setEnabled(True)
            self.updateTime(self.dateTimeEdit_start, startTime, date=True)
            self.myTimer.start(1000)

    def save_timer(self):
        # log time
        self.stop_timer(stop=True)
        self.prev_timer = str(self.timerTime)
        self.xml_data.find("prev_timer").text = str(self.prev_timer)
        self.log_time()
        self.timer =  self.timer + self.timerTime
        self.xml_data.find('timer').text = str(self.timer)
        self.reset_timer()
        self.calculate()
        
    def stop_timer(self, stop=False):
        # timer stop and log
        if stop:  
            self.log_end_time=time.strftime("%I:%M:%S", time.localtime(time.time()))
        else: 
            self.log_pause_time.append(time.strftime("%I:%M:%S", time.localtime(time.time())))
        self.myTimer.stop()
        
    def updateTimer(self):
        #Count the seconds
        self.timerTime+=1
        self.updateTime(self.timeEdit_timer, self.timerTime, date=False)    

    def updateTime(self, name, timer, date=False):
        # update time to load to UI
        if type(timer)==time.struct_time:    
            times = QtCore.QDateTime(timer[0],timer[1],timer[2],timer[3],timer[4],timer[5])
        elif type(timer) == int: 
            times = str(datetime.timedelta(seconds=(timer))).split(":")
            times = QtCore.QTime(int(times[0]), int(times[1]), int(times[2]))  
        elif type(timer) == str:        
            if "/" in timer:
                try: times = time.strptime(timer, "%Y/%m/%d")
                except: times = time.strptime(timer, "%m/%d/%y")
                times = QtCore.QDateTime(times[0],times[1],times[2],0,0,0)
            elif ":" in timer:
                times = QtCore.QTime(int(timer.split(":")[0]), int(timer.split(":")[1]), int(timer.split(":")[2])) 
            elif ", " in timer:
                try: times = time.strptime(str(timer), '%b %d, %Y')
                except: times = time.strptime(str(timer), '%B %d, %Y')
                times = QtCore.QDateTime(times[0],times[1],times[2],0,0,0)
            elif " " in timer:
                try: times = time.strptime(timer, "%d %b %Y")
                except: times = time.strptime(timer, "%d %B %Y")
                times = QtCore.QDateTime(times[0],times[1],times[2],0,0,0)
            else:            
                times = 0
        else:
            times = time.localtime(timer)
            times = QtCore.QDateTime(times[0],times[1],times[2],times[3],times[4],times[5])
        
        try: name.setDateTime(times)
        except: name.setTime(times)
        
    def reset_timer(self):
        #Reset the timer and UI
        self.label_timer.setText( str(datetime.timedelta(seconds=(self.timer))) )
        self.timerTime = 0
        self.timeEdit_timer.setTime(QtCore.QTime(0,0,0))
        self.dateTimeEdit_start.setTime(QtCore.QTime(9,0,0))
        self.pushButton_save.setEnabled(False)
        self.pushButton_save.setText("SAVE")
        self.pushButton_start_pause.setText("START")
        self.saveDefaults()
        
    def log_time (self, output=False):
        #Save the timer data to a log
        if self.log_restart_time:
            self.log_middle_time=("\t".join(["%s\t%s"%(a,b) for a, b in itertools.izip_longest(self.log_pause_time, self.log_restart_time, fillvalue="")]))
        if not output: output="%s\t%s\t\t%s\t%s\t%s\n"%(time.strftime("%B %d, %Y", time.localtime(time.time())), str(datetime.timedelta(seconds=(self.timerTime))), self.log_start_time, self.log_middle_time, self.log_end_time)
        self.log_out.write(output)
        #unlock the file
        self.log_out.close()
        self.log_out = open(self.logfile,"a")
        self.log_restart_time = []
        self.log_pause_time = []
        self.log_middle_time = ""
        
        
if __name__ == "__main__":
    # Automatically starts the program
    m = Main()
    m.show()
    # I use instance() because that way we don't have to hunt for the app variable.
    QtGui.QApplication.instance().exec_() #for py2
    if hasattr(sys, 'last_traceback'):
        pdb.pm()