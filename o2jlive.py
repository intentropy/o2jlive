#!/bin/python
'''
O2J Live
   o2jlive.py
    Written By:  Shane Hutter
    
     This program is licensed under the GNU GPL version 3
    
     Required Dependencies: python >= 3.5, liblo, cython, JACK-Client, cifi, jack, and pyliblo
 
    This program acts as a link between OSC and the Jack transport/MIDI
    It acts as a Jack client, and as an OSC server/client.
    It also defines loop sections in the jack timeline and allows for
    the JACK transport to move between multiple loop sections
    it is intended to be controlled via OSC
'''

import liblo, sys, jack

#PROGRAM CONST
ERROR=255
CLEAN=0

#TIME CONST
MINUTE=60
TIME_BPM_INDEX=0
TIME_SIGN_INDEX=1
TIME_SIGD_INDEX=2
TIME_EVENT_TYPE=0

#OSC CONST
OSC_CLIENT_IP_ARG=0
OSC_CLIENT_PORT_ARG=1
OSC_CLIENT_IP_INDEX=0
OSC_CLIENT_PORT_INDEX=1
OSC_TARGET_INDEX=0
OSC_MESSAGES_INDEX=1
OSC_MESSAGE_PATH_INDEX=0
OSC_EVENT_TYPE=1
JACK_TRANSPORT_STATE_OSC_ARG_INDEX=0
JACK_REMOTE_TRANSPORT_STATE_OSC_ARG_INDEX=0
JACK_REMOTE_TRANSPORT_SERVER_ID_OSC_ARG_INDEX=1
JACK_ALL_TRANSPORT_STATE_OSC_ARG_INDEX=0
LOOP_JUMP_OVERRIDE_OSC_ARG_INDEX=0
LOOP_JUMP_BYPASS_OSC_ARG_INDEX=0
LOOP_JUMP_BYPASS_ONCE_OSC_ARG_INDEX=0
EXIT_OSC_ARG_INDEX=0
JACK_TRANSPORT_PATH='/o2jlive/jack/transport'
JACK_ALL_TRANSPORT_PATH='/o2jlive/jack.all/transport'
JACK_REMOTE_TRANSPORT_PATH='/o2jlive/jack.remote/transport'
O2JLIVE_EXIT_PATH='/o2jlive/exit'
LOOP_JUMP_OVERRIDE_PATH='/o2jlive/looping/jump.override'
LOOP_JUMP_BYPASS_PATH='/o2jlive/looping/bypass'
LOOP_JUMP_BYPASS_ONCE_PATH='/o2jlive/looping/bypass.once'

#JACK CONST
JACK_TRANSPORT_DATA_INDEX=1
JACK_TRANSPORT_STOP_STATE=0
JACK_TRANSPORT_START_STATE=1
JACK_TRANSPORT_ZERO_STATE=2
JACK_TRANSPORT_LOCATION_INDEX='frame'
CURRENT_FRAME_INDEX=1
PREVIOUS_FRAME_INDEX=0
FRAMENUM_INDEX=0
EVENT_TYPE_INDEX=1
EVENT_DATA_INDEX=2
JUMP_TARGET_FILE_INDEX=1
JUMP_TARGET_INDEX=0
NULL_JUMP_TARGET=-1
LOOP_JUMP_EVENT_TYPE=2
FRAME_ZERO=0

#program vars
mainLoop=True
totalArgs=len(sys.argv)
eventData=[]

#jump override
overrideJumpEvent=False
newJumpTarget=0

#osc vars
oscServerId=[]
oscClientTarget=[]
sendOscMessages=[]

#jack vars
jackClientName='O2J Live'
trackFrame=[0]*2
barBeatNum=[0]*2
lastLoopJumpEventFrame=-1
lastOtherEventsFrame=-1
transportLatencyCalibrate=4
transportMoved=False
bypassLoops=False
bypassLoopsOnce=False
preferedLatency=5

#load config file
#CONFIG CONST
CONFIG_PROPERTY_ARG=0
CONFIG_VALUE_ARG=1
#config
configFileName='o2jlive.conf'
configLines=open(configFileName,'r').read().split('\n')
for lineRead in configLines:
    if (lineRead!="") and (lineRead.strip()[0:1]!='#'):
        #verbosity settings
        if lineRead.split()[CONFIG_PROPERTY_ARG]=='o2jlive.verbose_frame_num':
            global verboseFrameNum
            verboseFrameNum=bool(int(lineRead.split()[CONFIG_VALUE_ARG]))           
        if lineRead.split()[CONFIG_PROPERTY_ARG]=='o2jlive.verbose_bar_beat':
            global verboseBarBeat
            verboseBarBeat=bool(int(lineRead.split()[CONFIG_VALUE_ARG]))
        if lineRead.split()[CONFIG_PROPERTY_ARG]=='o2jlive.verbose_time_change':
            global verboseTimeChange
            verboseTimeChange = bool(int(lineRead.split()[CONFIG_VALUE_ARG]))
        if lineRead.split()[CONFIG_PROPERTY_ARG]=='o2jlive.verbose_loaded_data':
            global verboseLoadedData
            verboseLoadedData=bool(int(lineRead.split()[CONFIG_VALUE_ARG]))
        if lineRead.split()[CONFIG_PROPERTY_ARG]=='o2jlive.verbose_latency':
            global verboseLatency
            verboseLatency=bool(int(lineRead.split()[CONFIG_VALUE_ARG]))       
        if lineRead.split()[CONFIG_PROPERTY_ARG]=='o2jlive.verbose_event_data':
            global verboseEventData
            verboseEventData=bool(int(lineRead.split()[CONFIG_VALUE_ARG]))
        if lineRead.split()[CONFIG_PROPERTY_ARG]=='o2jlive.verbose_osc_incoming':
            global verboseOscIn
            verboseOscIn=bool(int(lineRead.split()[CONFIG_VALUE_ARG]))
        if lineRead.split()[CONFIG_PROPERTY_ARG]=='o2jlive.verbose_osc_outgoing':
            global verboseOscOut
            verboseOscOut=bool(int(lineRead.split()[CONFIG_VALUE_ARG]))
        if lineRead.split()[CONFIG_PROPERTY_ARG]=='o2jlive.verbose_osc_serverlist':
            global verboseOscServer
            verboseOscServers=bool(int(lineRead.split()[CONFIG_VALUE_ARG]))
            
        #JACK
        if lineRead.split()[CONFIG_PROPERTY_ARG]=='o2jlive.midi_inport_total':
            global midiInPortTotal
            global midiInName
            midiInPortTotal=int(lineRead.split()[CONFIG_VALUE_ARG])
            midiInName=[''] * midiInPortTotal
        if lineRead.split()[CONFIG_PROPERTY_ARG]=='o2jlive.midi_outport_total':
            global midiOutPortTotal
            global midiOutName
            midiOutPortTotal=int(lineRead.split()[CONFIG_VALUE_ARG])
            midiOutName=[''] * midiOutPortTotal
        if lineRead.split()[CONFIG_PROPERTY_ARG]=='o2jlive.basic_mode_bpm':
            global basicBpm
            basicBpm=int(lineRead.split()[CONFIG_VALUE_ARG])
        if lineRead.split()[CONFIG_PROPERTY_ARG]=='o2jlive.basic_mode_time_n':
            global basicTimeSigN
            basicTimeSigN=int(lineRead.split()[CONFIG_VALUE_ARG])
        if lineRead.split()[CONFIG_PROPERTY_ARG]=='o2jlive.basic_mode_time_d':
            global basicTimeSigD
            basicTimeSigD=int(lineRead.split()[CONFIG_VALUE_ARG])
                
        #OSC
        if lineRead.split()[CONFIG_PROPERTY_ARG]=='o2jlive.osc_listen_port':
            global oscListenPort
            oscListenPort=int(lineRead.split()[CONFIG_VALUE_ARG])
        if lineRead.split()[CONFIG_PROPERTY_ARG]=='o2jlive.verbose_osc_listen_port':
            global verboseOscListenPort
            verboseOscListenPort=bool(lineRead.split()[CONFIG_VALUE_ARG])
        if lineRead.split()[CONFIG_PROPERTY_ARG]=='o2jlive.osc_server':
            oscServerId.append(lineRead.split()[CONFIG_VALUE_ARG].split(':'))

#create the JACK client
jack_client = jack.Client(jackClientName)
#create in and out ports (MIDI to OSC to MIDI)
for midiInPortReg in range(0,midiInPortTotal):
    midiInName[midiInPortReg]='MIDI to OSC '+str(midiInPortReg)
    jack_client.midi_inports.register(midiInName[midiInPortReg])
for midiOutPortReg in range(0,midiOutPortTotal):
    midiOutName[midiOutPortReg]='OSC to MIDI '+str(midiOutPortReg)
    jack_client.midi_outports.register(midiOutName[midiOutPortReg])
jack_client.activate()
jack_client.transport_stop()
jackLatency=int((jack_client.blocksize*2/jack_client.samplerate)*1000)
if verboseLatency==True:
    print('JACK latency detected at:', end=' ')
    print(jackLatency, end='')
    print('ms')
if jackLatency>preferedLatency:
    print('Warning:  JACK is not setup for very low latency!')
    print('          Errors may occur during looping.')
    print('          To prevent this use a smaller Frames/Period')

#create OSC Server
try:
    osc_server=liblo.Server(oscListenPort)
    #verbose listen port
    if verboseOscListenPort==True:
        print('Listening for OSC messages on port', end=' ')
        print(oscListenPort)
except liblo.ServerError as  error:
    print(str(error))
    sys.exit(ERROR)

#setup to connect to remote OSC servers
for oscServerNum in range(0,len(oscServerId)):
    #make port number an int
    oscServerId[oscServerNum][OSC_CLIENT_PORT_INDEX]=int(oscServerId[oscServerNum][OSC_CLIENT_PORT_INDEX])
    #verbose the hosts that the clients will connect to
    if verboseOscServers==True:
        print('Server #', end='')
        print(oscServerNum, end=' is ')
        print(oscServerId[oscServerNum][OSC_CLIENT_IP_INDEX]+":"+str(oscServerId[oscServerNum][OSC_CLIENT_PORT_INDEX]))
    
#set up multiple client targets (shout at servers)
for oscServerNum in range(0,len(oscServerId)):
    try:
        oscClientTarget.append(liblo.Address(oscServerId[oscServerNum][OSC_CLIENT_IP_INDEX], oscServerId[oscServerNum][OSC_CLIENT_PORT_INDEX]))
    except liblo.AddressError as error:
        print(str(error))
        sys.exit(ERROR)

#check if file is being loaded
if totalArgs==1:
    print('No file loaded.  Starting in basic mode.')
    basicMode=True
elif totalArgs==2:
    global loadFileName
    basicMode=False
    loadFileName=sys.argv[1]
else:
    print('Inappropriate number of arguments have been passed.  Exiting...')
    sys.exit(ERROR)
        
#load file or resort to basic mode
if basicMode==False:
    try:
        #load a song file here
        #file load vars
        loadFileLines=open(loadFileName,'r').read().split('\n')
        fileLineNum=0
        eventCount=0
        timeEventList=[]
        timeEventData=[]
        loopStartMarker=[]
        loopJumpEventList=[]
        loopJumpEventData=[]
        oscEventList=[]
        oscEventData=[]
        oscMessageList=[]
        oscMessageRead=False
        for lineRead in loadFileLines:
            fileLineNum+=1
            if fileLineNum==1:
                if (int(lineRead)!=jack_client.samplerate):
                    #check for matching sample rates
                    print(loadFileName, end="'s ")
                    print('sample rate does not match the JACK sample rate.')
                    print(loadFileName, end=': ')
                    print(int(lineRead))
                    print('JACK: ', end='')
                    print(jack_client.samplerate)
                    print('Exiting...')
                    sys.exit(ERROR)
            else:
                if lineRead!='' and lineRead.strip()[0:1]!='#':
                    if lineRead.strip()[0:1]!='/':
                        if oscMessageRead==True:
                            '''
                            this marks the end of reading an
                            oscMessageList.
                            finish appending the oscEventData list
                            '''
                            oscMessageRead=False
                            oscEventList.append(oscMessageList)
                            oscEventData.append(oscEventList[1:])
                            eventData.append(oscEventData)
                            oscMessageList=[]
                    if lineRead.strip()[0:1]=='*':
                        #save in time map events
                        #store timeEvent vars
                        timeEventList=lineRead.split()
                        for listElement in range(1,len(timeEventList)):
                            timeEventList[listElement]=int(timeEventList[listElement])                            
                        timeFrameNum=int(timeEventList[FRAMENUM_INDEX][1:])
                        timeEventData=[timeFrameNum,TIME_EVENT_TYPE]
                        timeEventData.append(timeEventList[1:])
                        #store info in eventData
                        eventData.append(timeEventData)
                    if lineRead.strip()[0:1]=='$':
                        #save in loopStart (marker, not event)
                        loopStartMarker.append(int(lineRead.split()[FRAMENUM_INDEX][1:]))                  
                    if lineRead.strip()[0:1]=='!':
                        #save in time loopJump events
                        loopJumpEventList=lineRead.split()
                        loopJumpEventList[JUMP_TARGET_FILE_INDEX]=int(loopJumpEventList[JUMP_TARGET_FILE_INDEX])
                        loopJumpFrameNum=int(loopJumpEventList[FRAMENUM_INDEX][1:])
                        loopJumpEventData=[loopJumpFrameNum,LOOP_JUMP_EVENT_TYPE]
                        loopJumpEventData.append(loopJumpEventList[1:])
                        #store info in eventData
                        eventData.append(loopJumpEventData)
                    if lineRead.strip()[0:1]=='@':
                        #save OSC data
                        #type 1
                        oscEventList=lineRead.split()
                        for listElement in range(1,len(oscEventList)):
                            oscEventList[listElement]=int(oscEventList[listElement])
                        oscFrameNum=int(oscEventList[FRAMENUM_INDEX][1:])
                        oscEventData=[oscFrameNum,OSC_EVENT_TYPE]
                        oscMessageRead=True
                    if lineRead.strip()[0:1]=='/':
                        #this is where the oscMessageList is built
                        oscMessage=lineRead.split()
                        for listElement in range(1,len(oscMessage)):
                            try:
                                oscMessage[listElement]=int(oscMessage[listElement])
                            except:
                                try:
                                    oscMessage[listElement]=float(oscMessage[listElement])
                                except:
                                    oscMessage[listElement]=str(oscMessage[listElement])
                        oscMessageList.append(oscMessage)
                    if lineRead.strip()[0:1]=='~':
                        #end of file
                        print('File', end=' ')
                        print(loadFileName, end=' ')
                        print('has been loaded!')
        #Set initial bpm and time sig
        timeSigSet=False
        initTimeData=0
        for eventNum in range(0,len(eventData)):
            if eventData[eventNum][FRAMENUM_INDEX]==FRAME_ZERO and eventData[eventNum][EVENT_TYPE_INDEX]==FRAME_ZERO:
                timeSigSet=True
                initTimeData=eventNum
            #verbose loaded event
            if verboseLoadedData==True:
                print(eventData[eventNum])
        #verbose loaded start points
        if verboseLoadedData==True:
            for loopStartNum in range(0,len(loopStartMarker)):
                print('Loop Start point at frame', end=' ')
                print(loopStartMarker[loopStartNum])
        if timeSigSet==True:
            bpm=int(eventData[initTimeData][EVENT_DATA_INDEX][TIME_BPM_INDEX])
            timeSigN=int(eventData[initTimeData][EVENT_DATA_INDEX][TIME_SIGN_INDEX])
            timeSigD=int(eventData[initTimeData][EVENT_DATA_INDEX][TIME_SIGD_INDEX])            
        else:
            print('Initial time signature was not set.  Exiting...')
            sys.exit(ERROR)
    except:        
        print(loadFileName, end=' ')
        print('file does not exist or is corrupt.  Exiting...')
        sys.exit(ERROR)
elif basicMode==True:
    #no file loaded, use basic mode values
    bpm=basicBpm
    timeSigN=basicTimeSigN
    timeSigD=basicTimeSigD

def timeChange(bpmChange, timeSigNChange, timeSigDChange):
    global bpm
    global timeSigN
    global timeSigD
    currentTime=[bpm, timeSigN, timeSigD]
    newTime=[bpmChange, timeSigNChange, timeSigDChange]
    if currentTime!=newTime:
        bpm = bpmChange
        timeSigN = timeSigNChange
        timeSigD = timeSigDChange
        if verboseTimeChange == True:
            print('Time has changed to: '+str(timeSigN)+'/'+str(timeSigD)+' @ '+str(bpm)+'bpm')
    return
    
def sendOSC(target, path, args):
    #send osc messages in this function
    libloSend='liblo.send(target, path'
    for eachArg in range(0,len(args)):
        libloSend+=', args['+str(eachArg)+']'
    libloSend+=')'
    exec(libloSend)
    return
    
def checkOtherEvents():
    #this function checks all non loopJump events
    lastOtherEventsFrame=trackFrame[CURRENT_FRAME_INDEX]
    for eventNum in range(0,len(eventData)):
        if eventData[eventNum][FRAMENUM_INDEX]>trackFrame[PREVIOUS_FRAME_INDEX] and eventData[eventNum][FRAMENUM_INDEX]<=trackFrame[CURRENT_FRAME_INDEX] and eventData[eventNum][EVENT_TYPE_INDEX]!=LOOP_JUMP_EVENT_TYPE:
            #time change events
            if eventData[eventNum][EVENT_TYPE_INDEX]==TIME_EVENT_TYPE:
                timeChange(eventData[eventNum][EVENT_DATA_INDEX][TIME_BPM_INDEX], eventData[eventNum][EVENT_DATA_INDEX][TIME_SIGN_INDEX], eventData[eventNum][EVENT_DATA_INDEX][TIME_SIGD_INDEX])
                #verbose time change events
                if verboseEventData == True:
                    print('Time changed at frame '+str(eventData[eventNum][FRAMENUM_INDEX])+' to '+str(eventData[eventNum][EVENT_DATA_INDEX][TIME_SIGN_INDEX])+'/'+str(eventData[eventNum][EVENT_DATA_INDEX][TIME_SIGD_INDEX])+' @ '+str(eventData[eventNum][EVENT_DATA_INDEX][TIME_BPM_INDEX])+'bpm')
            #send osc events
            if eventData[eventNum][EVENT_TYPE_INDEX]==OSC_EVENT_TYPE:
                for message in range(0,len(eventData[eventNum][EVENT_DATA_INDEX][OSC_MESSAGES_INDEX])):
                    sendOSC(eventData[eventNum][EVENT_DATA_INDEX][OSC_TARGET_INDEX], eventData[eventNum][EVENT_DATA_INDEX][OSC_MESSAGES_INDEX][message][0], eventData[eventNum][EVENT_DATA_INDEX][OSC_MESSAGES_INDEX][message][1:])
            #verbose event data
            if verboseEventData==True:
                print(eventData[eventNum])
    return
    
def moveTransport(location):
    #use this function to both move the transport, and confirm that
    '''
    if config is set to relocate other transports remotely then send
    oscmessages here to the other hosts to relocate them
    intended to relocate with O2J Transport
    '''
    #checl that the transport is at the corect location
    jack_client.transport_locate(location)
    currentLoc=jack_client.transport_query()[JACK_TRANSPORT_DATA_INDEX][JACK_TRANSPORT_LOCATION_INDEX]
    while currentLoc!=location:
        if currentLoc>location:
            jack_client.transport_locate(location)
        currentLoc=jack_client.transport_query()[JACK_TRANSPORT_DATA_INDEX][JACK_TRANSPORT_LOCATION_INDEX]
    #check for last time change that occured before or on new location
    currentTime=[bpm, timeSigN, timeSigD]
    newTime=currentTime
    for checkPrevTime in range(0,len(eventData)):
        if eventData[checkPrevTime][EVENT_TYPE_INDEX]==TIME_EVENT_TYPE and eventData[checkPrevTime][FRAMENUM_INDEX]<=location:
            newTime=eventData[checkPrevTime][EVENT_DATA_INDEX]
    if newTime!=currentTime:
        timeChange(newTime[TIME_BPM_INDEX], newTime[TIME_SIGN_INDEX], newTime[TIME_SIGD_INDEX])
    trackFrame[PREVIOUS_FRAME_INDEX]=currentLoc-jack_client.blocksize
    trackFrame[CURRENT_FRAME_INDEX]=currentLoc
    global transportMoved
    transportMoved=True
    checkOtherEvents()
    return
moveTransport(FRAME_ZERO)
transportMoved=False

def calcBarBeatToFrames(bar, beat):
    #this function takes a bar and beat and calculates a frame number
    #calculate beatLen and barLen
    '''
    THIS IS BUGGY!
    I need to work out a method of handling the time info as
    a time map and not as events.
    The problem is, after a time change event the verbose
    bar beats are calculated as if the song was always in that time.
    '''
    barLenSec=bpm/MINUTE
    beatLenSec=barLenSec/timeSigN
    barLenFrames=jack_client.samplerate*barLenSec
    beatLenFrames=jack_client.samplerate*beatLenSec
    #calculate frame Number
    frameNum=int((bar*barLenFrames)+(beat*beatLenFrames))
    return frameNum

def calcFramesToBarBeat(frame):
    #this function uses frames to calculate Bar and Beat
    #calculate beatLen and barLen
    barLenSec=bpm/MINUTE
    beatLenSec=barLenSec/timeSigN
    barLenFrames=jack_client.samplerate*barLenSec
    beatLenFrames=jack_client.samplerate*beatLenSec
    #calculate beat and bar number
    #(rounds down, or frame falls in this beat)
    #bar:
    bar=int(frame/barLenFrames)
    #beat:
    beat=int((frame-(bar*barLenFrames))/beatLenFrames)
    barBeatNum=[bar,beat]
    return barBeatNum

def checkLoopJumpEvents():
    #This function handles loopJumps
    lastLoopJumpEventFrame=trackFrame[CURRENT_FRAME_INDEX]
    global overrideJumpEvent
    global newJumpTarget
    global bypassLoops
    global bypassLoopsOnce
    for eventNum in range(0,len(eventData)):
        if eventData[eventNum][FRAMENUM_INDEX]-jack_client.blocksize*transportLatencyCalibrate>trackFrame[PREVIOUS_FRAME_INDEX] and eventData[eventNum][FRAMENUM_INDEX]-jack_client.blocksize*transportLatencyCalibrate<=trackFrame[CURRENT_FRAME_INDEX] and eventData[eventNum][EVENT_TYPE_INDEX]==LOOP_JUMP_EVENT_TYPE and bypassLoops==False:
            if bypassLoopsOnce==False:
                if overrideJumpEvent==False:
                    #loopJumpPoint
                    moveTransport(loopStartMarker[eventData[eventNum][EVENT_DATA_INDEX][JUMP_TARGET_INDEX]])
                    if verboseEventData==True:
                        print('Transport jumped to frame', end=' ')
                        print(loopStartMarker[eventData[eventNum][EVENT_DATA_INDEX][JUMP_TARGET_INDEX]])
                else:
                    #jump override
                    moveTransport(loopStartMarker[newJumpTarget])
                    overrideJumpEvent=False
                    #verbose jump event
                    if verboseEventData==True:
                        print('Transport jumped to frame', end=' ')
                        print(loopStartMarker[newJumpTarget])
            else:
                bypassLoopsOnce=False
    return

def loopJumpOverride(path, args):
    #override the next loopJump's loopStartMarker with OSC value
    argNewJumpTarget=int(args[LOOP_JUMP_OVERRIDE_OSC_ARG_INDEX])
    if argNewJumpTarget!=NULL_JUMP_TARGET and argNewJumpTarget<=len(loopStartMarker)-1:
        #-1s are to be ignored preventing triggering the event twice
        #only pass to available loopStartPoints
        global overrideJumpEvent
        global newJumpTarget
        overrideJumpEvent=True
        newJumpTarget=argNewJumpTarget
        #verbose incoming OSC
        if verboseOscIn==True:
            print('Loop Override!  Next loop starting point is', end=' ')
            print(newJumpTarget)
    return

def verboseTime():
    '''
    There are some known issue involving time changes
    frame blocks where a time is 4/4 must be taken into account when
    calculating beat/bar for a change to 3/4, etc...
    This should be fixed in the beat bar function
    This isn't vital, I will eventually fix it
    Events are triggered with frames, so this only currently effects 
    verbosity of bar/beat
    '''
    #verbose BarBeat
    if verboseBarBeat==True:
        if calcFramesToBarBeat(trackFrame[PREVIOUS_FRAME_INDEX])!=calcFramesToBarBeat(trackFrame[CURRENT_FRAME_INDEX]):
            print(calcFramesToBarBeat(trackFrame[CURRENT_FRAME_INDEX]))

    #verboseFrameNum=True
    #debug print trackFrame, make verbosity vars in config
    if verboseFrameNum==True:
        if trackFrame[CURRENT_FRAME_INDEX]!=trackFrame[PREVIOUS_FRAME_INDEX]:
            print(trackFrame[CURRENT_FRAME_INDEX])
    return


def trackTransport():
    global trackFrame
    #track the transport
    trackFrame[PREVIOUS_FRAME_INDEX]=trackFrame[CURRENT_FRAME_INDEX]
    trackFrame[CURRENT_FRAME_INDEX]=jack_client.transport_query()[JACK_TRANSPORT_DATA_INDEX][JACK_TRANSPORT_LOCATION_INDEX]
    return

#-------------INCOMING-OSC-MESSAGE-FUNCTIONS-------------------
#    Store path names in CONST!
def jackTransport(path, args):
    #verbose incoming OSC
    if verboseOscIn==True:
        print("Incoming OSC: "+path+" "+str(args[JACK_TRANSPORT_STATE_OSC_ARG_INDEX]))
    #capture args
    jackTransportState = int(args[JACK_TRANSPORT_STATE_OSC_ARG_INDEX])
    if jackTransportState == JACK_TRANSPORT_STOP_STATE:
        jack_client.transport_stop()
        print('Jack Transport has STOPPED')
    if jackTransportState == JACK_TRANSPORT_START_STATE:
        jack_client.transport_start()
        print('Jack Transport has STARTED')
    if jackTransportState == JACK_TRANSPORT_ZERO_STATE:
        moveTransport(FRAME_ZERO)
        print('Jack Transport was sent to BEGINNING')
    return
        
def jackRemoteTransport(path, args):
    #Have it check the len(args) here and if < 2 assume arg[1]=0
    if len(args)<2:
        args.append(0)
    #verbose incoming OSC
    if verboseOscIn==True:
        print("Incoming OSC: "+path+" "+str(args[JACK_REMOTE_TRANSPORT_STATE_OSC_ARG_INDEX]))
    #capture args
    jackTransportState = int(args[JACK_REMOTE_TRANSPORT_STATE_OSC_ARG_INDEX])
    serverTargetId = int(args[JACK_REMOTE_TRANSPORT_SERVER_ID_OSC_ARG_INDEX])
    #Send OSC to specific server defined sent as arg
    sendOSC(serverTargetId, JACK_TRANSPORT_PATH, jackTransportState)
    return
    
def jackAllTransport(path, args):
    #verbose incoming OSC
    if verboseOscIn==True:
        print('Incoming OSC: '+path+' '+str(args[JACK_ALL_TRANSPORT_STATE_OSC_ARG_INDEX]))
    #capture args
    jackTransportState = int(args[JACK_ALL_TRANSPORT_STATE_OSC_ARG_INDEX])
    #Send OSC to all servers defined in config file
    for oscServerNum in range(0,len(oscServerId)):
        sendOSC(oscServerNum, JACK_TRANSPORT_PATH, sendOscMessages)
    #Change local JACK transport state
    if jackTransportState == JACK_TRANSPORT_STOP_STATE:
        jack_client.transport_stop()
        print('Jack Transport has STOPPED')
    if jackTransportState == JACK_TRANSPORT_START_STATE:
        jack_client.transport_start()
        print('Jack Transport has STARTED')
    if jackTransportState == JACK_TRANSPORT_ZERO_STATE:
        moveTransport(FRAME_ZERO)
        print('Jack Transport was sent to BEGINNING')
        
def loopJumpBypass(path, args):
    #verbose incoming OSC
    if verboseOscIn==True:
        print("Incoming OSC: "+path+" "+str(args[LOOP_JUMP_BYPASS_OSC_ARG_INDEX]))
    global bypassLoops
    bypassLoops=bool(args[LOOP_JUMP_BYPASS_OSC_ARG_INDEX])
    return

def loopJumpBypassOnce(path, args):
    #verbose incoming OSC
    if verboseOscIn==True:
        print("Incoming OSC: "+path+" "+str(args[LOOP_JUMP_BYPASS_ONCE_OSC_ARG_INDEX]))
    global bypassLoopsOnce
    bypassLoopsOnce=bool(args[LOOP_JUMP_BYPASS_ONCE_OSC_ARG_INDEX])
    return

def exitProgram(path, args):
    #verbose incoming OSC
    if verboseOscIn==True:
        print("Incoming OSC: "+path+" "+str(args[EXIT_OSC_ARG_INDEX]))
    #terminate main loop
    if bool(args[EXIT_OSC_ARG_INDEX]) == True:
        print('Exiting...')
        global mainLoop
        mainLoop=False
    return

#register methods for recieveing OSC command
osc_server.add_method(JACK_TRANSPORT_PATH, None, jackTransport)
osc_server.add_method(JACK_ALL_TRANSPORT_PATH, None, jackAllTransport)
osc_server.add_method(JACK_REMOTE_TRANSPORT_PATH, None, jackRemoteTransport)
osc_server.add_method(O2JLIVE_EXIT_PATH, None, exitProgram)
osc_server.add_method(LOOP_JUMP_OVERRIDE_PATH, None, loopJumpOverride)
osc_server.add_method(LOOP_JUMP_BYPASS_PATH, None, loopJumpBypass)
osc_server.add_method(LOOP_JUMP_BYPASS_ONCE_PATH, None, loopJumpBypassOnce)
#-------------------------------------------------------------

#main loop
print('Ready...')
while mainLoop!=False:

    #Track the transport
    trackTransport()
    
    #check for events
    if trackFrame[CURRENT_FRAME_INDEX]!=lastLoopJumpEventFrame:
        checkLoopJumpEvents()

    if trackFrame[CURRENT_FRAME_INDEX]!=lastOtherEventsFrame and transportMoved==False:
        checkOtherEvents()
    else:
        transportMoved=False

    #display transport location verbosity
    verboseTime()

    #listen for incoing OSC messages
    osc_server.recv(jackLatency)
    
#shutdown
jack_client.transport_stop()
jack_client.deactivate()
sys.exit(CLEAN)
