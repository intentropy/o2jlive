# o2jlive
A python based link between the JACK Audio Connection Kit, and Open Sound Control


Basic Mode:

Running o2jlive.py without passing a file as an argument will start basic mode.  Basic mode only allows for the direct control of the jack transport.


Loading Files:

Passing a file name as an argument into o2jlive.py will load loop start markers, loop jump events, time changes, and osc message send events, into the program.  Files are ascii text files.  The first line of the file indicates the samplerate of the file.
    time changes:  Lines beggining with '*', *frame_number tempo time_signature_numerator time_signature_denominator
      One time change must be delared at frame 0 to set initial time signature and tempo
  
    loop start markers:  Lines beggining with '$', $frame_number
      these markers define the starting points for loops
  
    loop jump events:  Lines beggining with '!', !frame_number loop_start_point
      these events force the jack transport back to a loop start point
  
    osc message send events:  Lines beggining with '@', @frame_number server_id_number
      these events will send a list of osc messages to a server
      the servers are defined i the config file
      all following lines until next event are loaded as osc messages to be sent at this event
        /osc/path value00 value01 value03 etc...
  
    ~END OF FILE~:  Currently there must be a line at the end of the file beggining with '~'


Controlling via OSC:

/o2jlive/exit
    1 = exit

/o2jlive/jack/transport
    0 = Stop
    1 = Play
    2 = Return to frame 0

/o2jlive/looping/jump.overide
    int = loop start point to jump to after end of current loop

/o2jlive/looping/bypass.once
    1 = continue on at end of current loop

/02jlive/looping/bypass
    0 = Do not bypass all loops
    1 = Bypass all loops


The configuration file:

Verbosity settings are set to 0 or 1 in order to deactivate or activate descrived verbosity

Jack Client settings set the tempo and time signature for basic mode.  It also sets the amount of midi imputs and outputs for OSC to MIDI conversion; although, this feature is not yet implimented.

OSC Client/Server settings are used to set up the listen port for o2jlive's osc server.  osc_server is used to define the addresses of 1 or more remote servers that o2jlive will create a client for.  These clients are automatically given a server_id_number, starting from zero, based on the order that they are listed in the configuration file.  These server_id_numbers are used to identify what remote server the o2jlive client uses to send osc message send events.

This is a work in progress.
