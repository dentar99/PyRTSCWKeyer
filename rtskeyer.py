#!/usr/bin/python3
#
# Author: Tom N4LSJ -- EXPERIMENTAL CODE ONLY FOR TINKERING
#                   -- USE AT YOUR OWN RISK ONLY
#                   -- AUTHOR ASSUMES NO LIABILITY
# 
# DTR/RTS Keyer for Raspberry Pi
# 
# This program is for radios that have USB to Serial built in,
# and have settings that say something like RTS keying or 
# DTR keying. (*ahem* 7300) or any other radio whose serial
# port (has to be wired right) will accept keying by either of
# these methods.
#
# You want to scroll down to def ptt_on and def ptt_off and
# comment out what you're NOT doing.
#
# If your radio is set to key DTR, then comment out the RTS ones.
# If your radio is set to key RTS, then comment out the DTR ones.
# The lines look like:
#
#        ser.setRTS(True)
#        ser.setDTR(True)
#
#        ser.setRTS(False)
#        ser.setDTR(False)
#
# also look for "serport =" and fix that to point to the 
# serial port the rig is on
#


import datetime
DEBUGTS=datetime.datetime.utcnow()

import time
import serial
import re

from tkinter import *
from tkinter.simpledialog import askstring
from tkinter.simpledialog import askinteger
from tkinter.simpledialog import askfloat
from tkinter.simpledialog import messagebox

from os.path import expanduser
from os import path
from time import sleep

global ee
global sending
global keyer
global ser
global mycall
global geom
global othercall
global configfn
global wpm
global cw


global tuning
global tuning_idt

global clock_id

global hotsend

global ser

hotsend=1
sending = 0
ee = 0
othercall=''
spinning=0
spinny=['|','/','-','\\']
curspinny=0
tuning=0
tuning_idt=''

################################# YOU SET THESE
mycall='CHANGEME'                # EMPTY ON PURPOSE
wpm="13"                        # WPM TO USE IF NO CONFIG FILE (FIX THIS)
serport="/dev/ttyS4"             # point this at your serial port
################################# END OF YOU SET THESE

ser = serial.Serial()
ser.port=serport
ser.baudrate=19200
ser.timeout=1
ser.parity=serial.PARITY_NONE
ser.bytesize=serial.EIGHTBITS
ser.stopbits=serial.STOPBITS_ONE
ser.setDTR(False)
ser.setRTS(False)
ser.open()


cw = {
"A" : ".-", "B" : "-...", "C" : "-.-.", "D" : "-..", "E" : ".", "F" : "..-.", 
"G" : "--.", "H" : "....", "I" : "..", "J" : ".---", "K" : "-.-", "L" : ".-..", 
"M" : "--", "N" : "-.", "O" : "---", "P" : ".--.", "Q" : "--.-", "R" : ".-.", 
"S" : "...", "T" : "-", "U" : "..-", "V" : "...-", "W" : ".--", "X" : "-..-", 
"Y" : "-.--", "Z" : "--..", "0" : "-----", "1" : ".----", "2" : "..---", 
"3" : "...--", "4" : "....-", "5" : ".....", "6" : "-....", "7" : "--...", 
"8" : "---..", "9" : "----.", "." : ".-.-.-", "?" : "..--..", "/" : "-..-.",
"," : "--..--", "!" : "-.-.--", "'" : ".----.", "\"" : ".-..-.", "(" : "-.--.",
")" : "-.--.-", "&" : ".-...", ":" : "---...", ";" : "-.-.-.", "_" : "..--.-",
"=" : "-...-", "+" : ".-.-.", "-" : "-....-", "$" : "...-..-", "@" : ".--.-",
"#" : "...-.-"
}

configfn=str(expanduser("~"))+"/.keyer.conf"

def updhotsbut(*args):
    global hotsend
    print("should be fixing button...")
    print("hotsend is "+str(hotsend))
    if (hotsend == 1):
        hots.config(text="Macro Immediate")
    else:
        hots.config(text="Macro Defer")

def hotstog(*args):
    global hotsend
    hotsend = int(1 - int(hotsend))
    updhotsbut()

def hovertxt(txt):
        hlabel.config(text=txt)

def hover(widg,txt):
        widg.bind("<Enter>",lambda evt, tt=txt: hovertxt(tt))
        widg.bind("<Leave>",lambda evt, tt="": hovertxt(tt))

def pttaction(val):
        if (val == 1):
                ptt_on()
        if (val == 0):
                ptt_off()

def starttuning(val,frombutton):
        global tuning
        global tuning_idt
        global keyer

        if (val > 1 and frombutton == 1 and tuning == 0):
            ptt_on()
            val = val - 1
            tuning_idt=root.after(1000,starttuning,val,0)
            tuning = 1
        else:
            root.after_cancel(tuning_idt)
            ptt_off()
            tuning = 0

def startclock(*args):
        global clock_id
        putdate()
        clock_id=root.after(500,startclock,'')

def putdate():
        now = str(datetime.datetime.utcnow())
        datelab.config(text=now[0:16]+" UTC")
        if (now[18] in {'0','2','4','6','8'}):
                datelab.config(bg='#00ff00')
        else:
                datelab.config(bg='#005500')

def numonly(val):
        for ch in val:
                if (not ch in ('0123456789')):
                        return False
        return True

def alnumslashonly(val):
        for ch in val:
                if (not ch in ('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/')):
                        return False
        return True

def cwonly(val):
        global cw
        for ch in val:
                ch=ch.upper()
                if (not ch in cw.keys() and ch != " " and ch != "<" and ch != ">"):
                        print ("BAD CHAR: ["+ch+"]")
                        return False
        return True

def WriteCfg():
        global configfn
        global hotsend

        fh=open(configfn,'w+')
        fh.write('wpm='+str(iwpm.get())+"\n")
        fh.write('mycall='+imycall.get()+"\n")
        fh.write('hotsend='+str(hotsend)+"\n")
        sx=root.geometry().replace('+',' ').split()[1]
        sy=root.geometry().replace('+',' ').split()[2]
        fh.write("geom=+"+sx+"+"+sy+"\n")
        for kid in macroframe.winfo_children():
                fh.write('macro='+str(kid['text'])+"\n")

        print("Saved config to "+configfn)

def MACGRIDNEW():
        mr = 0
        mc = 0
        gs=macroframe.grid_slaves()
        for s in gs:
                gi=s.grid_info()
                gir=gi['row']
                if (mr < gir):
                        mr = gir

        for s in gs:
                gi=s.grid_info()
                gir=gi['row']
                gic=gi['column']
                if (gir == mr and mc < gic):
                        mc = gic
        print ("max row is "+str(mr)+" and max col is "+str(mc))
        if (mc == 5):
                return mr+1, 1
        else:
                return mr, mc+1

def MACROREGRID():
        macbuts=[]
        gs=macroframe.grid_slaves()

        for r in range (1,100):
                for c in range (1,6):
                        for s in gs:
                                gi=s.grid_info()
                                rr=gi['row']
                                cc=gi['column']
                                if (r == rr and c == cc):
                                        macbuts.append(s)
        rr=1
        cc=1
        for m in macbuts:
                m.grid(row=rr, column=cc)
                cc=cc+1
                if (cc > 5):
                        cc=1
                        rr=rr+1
                                
                

        
def MAKEMACBUT(txt,rr,cc):
        bb=Button(macroframe, text=txt)
        bb.grid(row=rr,column=cc)
        hover(bb,"Hit to send "+txt+", or right click to edit.")
        bb.config(command=lambda widg=bb: RUNMACRO(widg))
        bb.bind("<ButtonRelease-3>", lambda ebe, widg=bb: EDITBTN(widg))
        return bb

def NEWMACRO(*args):
        rr,cc=MACGRIDNEW()
        bb=MAKEMACBUT('NEW MACRO',rr,cc)
        EDITBTN(bb)
        if (bb['text'] == 'NEW MACRO' or bb['text'] == ''):
                bb.destroy()

def EDITBTN(widg):
        newval = askstring('New Macro','Enter new macro. <C> is your call.  <I> is other call.',initialvalue=widg['text'])
        if (newval == ''):
                widg.destroy()
                MACROREGRID()
        else:
                widg.config(text=newval)

def EXPANDVARS(strinp):
        s1=strinp.upper()\
        .replace('<I>',iothercall.get().upper())\
        .replace('<C>',imycall.get().upper())\
        .replace('<AR>','+')\
        .replace('<SK>','#')\
        .replace('<KN>','(')\
        .replace('<AS>','&')
        s2=re.sub(r"<.*>?","",s1)
        s3=s2.replace('<','')\
        .replace('>','')
        return s3

def RUNMACRO(widg):
        global hotsend
        # DOING IN MULTIPLE STEPS.  SHUT UP
        string=EXPANDVARS(widg['text'])
        tempstr=cwinput.get()
        cwinput.delete(0,END)
        cwinput.insert(0,string)
        QUEUE()
        cwinput.delete(0,END)
        cwinput.insert(0,tempstr)
        if (hotsend == 1):
            STARTSEND()


def ReadCfg():
        global serport
        global keyer
        global geom
        global configfn
        global wpm
        global mycall
        global ee
        global hotsend

        if (not path.exists(configfn)):
                root.iconify()
                mycall=askstring("Call Sign","Please enter your call sign.").upper().strip()
                wpm=askinteger("WPM","Enter a default words per minute for CW.",minvalue=5,maxvalue=50)
                
                imycall.delete(0,END)
                imycall.insert(0,mycall)
                iwpm.delete(0,END)
                iwpm.insert(0,wpm)
                zz=Button(macroframe,\
                        text='SAMPLE MACRO')
                zz.config(command=lambda widg = zz: RUNMACRO(widg))
                zz.grid(row=0,column=1)
                WriteCfg()
                zz.destroy()
                imycall.delete(0,END)
                iwpm.delete(0,END)

        if (path.exists(configfn)):
                print ("Reading Config file now that it exists...")
                rr = 1
                cc = 1
                fh=open(configfn,'r')
                cfglines = fh.readlines()
                fh.close()
                for cfgline in cfglines:
                        items=cfgline.split('=')
                        if (items[0] == "hotsend"):
                                hotsend=int(items[1].strip())
                        if (items[0] == "wpm"):
                                wpm=items[1].strip()
                        if (items[0] == "mycall"):
                                mycall=items[1].strip()
                        if (items[0] == "geom"):
                                geom=items[1].strip()
                        if (items[0] == "macro"):
                                macrocontents=items[1].strip()
                                MAKEMACBUT(macrocontents,rr,cc)
                                cc = cc + 1
                        if (cc > 5):
                                rr = rr + 1
                                cc = 1


                return True
        else:
                print ("No config file yet.")
                return None

def Quitter(*args):
        global keyer
        WriteCfg()
        root.destroy()

def ptt_on():
        global ser
        ser.setRTS(True)
#        ser.setDTR(True)
        lcw.config(bg='#00ff00')
        root.update()

def ptt_off():
        global ser
        #global keyer
        #lcw.config(bg='#005500')
        ser.setRTS(False)
#        ser.setDTR(False)
        root.update()

def KEY(ch):
        global cw
        global keyer
        global wpm
        
        t = (1200.0/float(wpm))/1000.0
        ditlength = t
        dahlength = ditlength * 3
        ch = ch.upper()
        if (ch == " "):
                True
        else :
                for dd in cw[ch]:
                        if (dd == "-"):
                                ptt_on()
                                sleep(dahlength)
                                ptt_off()
                                sleep(ditlength)
                        if (dd == "."):
                                ptt_on()
                                sleep(ditlength)
                                ptt_off()
                                sleep(ditlength)
        root.update()
        sleep (dahlength)
        root.update()

def BCLEAR():
        cwinput.delete(0,END)
        QCLEAR()
        
def QCLEAR():
        global sending
        sending = 0
        queue.delete(0,END)
        
def QUEUE(*args):
        if (queue.get() != ""):
                queue.insert(END," ")
        queue.insert(END,cwinput.get().upper())
        cwinput.delete(0,END)

def STOP():
        global sending
        sending = 0
        lcw.config(bg='#d9d9d9')

def STARTSEND():
        global sending
        QUEUE()
        if (sending == 0):
                sending = 1
                SENDCW()

def SENDCW():
        global sending
        global wpm
        if (sending == 1):
                wpm=iwpm.get()
                qq = queue.get()
                qq = EXPANDVARS(qq)
                if (qq == ""):
                        print ("Nothing in queue")
                        sending = 0
                        return None
                key = qq[0]
                qq  = qq[1:]
                queue.delete(0,END)
                queue.insert(0,qq)
                root.update()
                KEY(key)
                root.update()
                if (queue.get() != ""):
                        SENDCW()
                else:
                        sending = 0
                        lcw.config(bg='#d9d9d9')

root=Tk()

cwframe=Frame(root,borderwidth=2,relief="groove")
callsframe=Frame(root,borderwidth=2,relief="groove")
macroframe=Frame(root,borderwidth=2,relief="groove")
helpframe=Frame(root,borderwidth=2,relief="groove")

root.bind("<Escape>",Quitter)
root.bind("<Control-w>",Quitter)
root.protocol("WM_DELETE_WINDOW", Quitter)
root.title("RTS Keyer")

macroframe.bind("<ButtonRelease-3>",NEWMACRO)

pttframe=Frame(cwframe)

# CW FRAME WIDGETS
lqueue = Label(cwframe, text="Queue:")
queue = Entry(cwframe, font="Courier", width=84, validate="key")
queue['validatecommand']=(queue.register(cwonly),'%P')

lcw = Label(cwframe, text="CW:")

cwinput = Entry(cwframe, font="Courier", width=40, validate="key")
cwinput['validatecommand']=(cwinput.register(cwonly),'%P')
cwinput.bind("<Return>",QUEUE)
cwinput.bind("<KP_Enter>",QUEUE)


lwpm = Label(cwframe,text="wpm:")
iwpm = Entry(cwframe, font = "Courier", width=2, validate="key")
iwpm['validatecommand']=(iwpm.register(numonly),'%P')
clr = Button(cwframe,text="clear queue", command=QCLEAR, width=8, fg="white",bg="blue") 
clrb = Button(cwframe,text="clear both", command=BCLEAR, width=8, fg="white",bg="blue") 
qcw = Button(cwframe,text="queue", command=QUEUE, width=8, bg="yellow") 
bcw = Button(cwframe,text="GO", command=STARTSEND, width=8, bg="green") 
scw = Button(cwframe,text="STOP", command=STOP, width=8, bg="red")

ptt = Button(pttframe,text="PTT", width=4)
tune = Button(pttframe,text="TUNE", width=5)
hots = Button(pttframe,text="Macro", width=15)

datelab = Label (cwframe, font="Helvetica 12 bold", text="YYYY-MM-DDDD HH:MM", width=23)
prosigns = Label(cwframe, font="Helvetica 10 bold", text="&=AS +=AR #=SK (=KN", width=23)

#HELP
hlabel=Label(helpframe,text="")

# CALLSIGN FRAME
lmycall = Label(callsframe, text="Your Station's Call:")
imycall = Entry(callsframe, width=13, validate="key", justify="center")
imycall['validatecommand']=(imycall.register(alnumslashonly),'%P')
lothercall = Label(callsframe, text="Other Station's Call:")
iothercall = Entry(callsframe, width=13, validate="key", justify="center")
iothercall['validatecommand']=(iothercall.register(alnumslashonly),'%P')
lnotes = Label(callsframe, text="<C> is replaced with your call.  <I> is replaced with other station's call.")

ptt.bind('<Button-1>',lambda evt, val = 1: pttaction(val))
ptt.bind('<ButtonRelease-1>',lambda evt, val=0: pttaction(val))

tune.bind('<Button-1>',lambda evt, val = float(10): starttuning(val,1))
hots.bind('<Button-1>',hotstog)


# FRAMES LAYOUT
cwframe.grid(row=4,column=1,columnspan=4,sticky='EW')
callsframe.grid(row=5,column=1,columnspan=4,sticky='EW')
macroframe.grid(row=6,column=1,columnspan=4,sticky='EW')
helpframe.grid(row=8,column=1,columnspan=4,sticky='EW')

# HELP LABEL
hlabel.grid(row=1,column=1)

# CW KEYING
clrb.grid(row=1,column=1)
clr.grid(row=1,column=2)
qcw.grid(row=1,column=3)
bcw.grid(row=1,column=4)
scw.grid(row=1,column=5)
lcw.grid(row=1,column=6)
cwinput.grid(row=1,column=7, columnspan=2)
lwpm.grid(row=1,column=9)
iwpm.grid(row=1,column=10)
lqueue.grid(row=2,column=1)
queue.grid(row=2,column=2,columnspan=9)

prosigns.grid(row=3,column=1, columnspan=2)
datelab.grid(row=3,column=2, columnspan=5)
pttframe.grid(row=3,column=8,columnspan=2)
ptt.grid(row=1,column=1)
tune.grid(row=1,column=2)
hots.grid(row=1,column=3)

# CALLSIGNS
lmycall.grid(row=1,column=1)
imycall.grid(row=1,column=2)
lothercall.grid(row=1,column=3)
iothercall.grid(row=1,column=4)
lnotes.grid(row=1,column=5)

hover(imycall,"Enter YOUR call here and it will be used in macros as <C>.")
hover(iothercall,"Enter OTHER call here and it will be used in macros as <I>.")
hover(iwpm,"Enter words per minute to send here.")

hover(cwframe,"This is the CW sending area.")
hover(callsframe,"Call sign area.")
hover(macroframe,"Right click in this area between buttons to make a new button.  Right click an already existing button to edit it.")
hover(helpframe,"This area is for helpful help message hovering.")

ReadCfg()
iwpm.insert(0,wpm)
imycall.insert(0,mycall)

root.geometry(geom)
startclock()
updhotsbut()
root.mainloop()

