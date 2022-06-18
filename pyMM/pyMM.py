import serial
from binascii import hexlify, unhexlify
from datetime import datetime
import time
import crcmod.predefined

class pyMM(object):
  def __init__(self, serialport = '/dev/ttyACM0', baudrate = 115200, timeout = 1):  
    print "Initializing pyMM"
    self.__serialport = serialport
    self.__baudrate = baudrate
    self.__timeout = timeout
    self.__ser = serial.Serial(serialport, baudrate, timeout = timeout)
    self.__ser.write('ATS0=1\r\n')
    self.__ser.write('AT+MS=B212\r\n')
    self.__frameID = '\x00'
    self.__ANI = []
    self.__nextACK = 0
    self.__nextFrame = 0
    self.__expectACKsendEOD = False
    self.__expectACKsendTRANS = False
    self.__outqueue = []
    self.__outqueuedesc = []
    self.__NCCANI = ['\x51', '\x45', '\x55', '\x11', '\x11']
    self.__expectACKsendWhat = ''
    self.__multiTable = False
    self.__tableOrder = [
                          'DLOG_MT_NCC_TERM_PARMS', # Vital table!
                          'DLOG_MT_CARD_TABLE_1', # Vital table!
                          'DLOG_MT_CARD_TABLE_2', # Vital table!
                          'DLOG_MT_CARD_TABLE_3', # Vital table!
                          'DLOG_MT_FCONFIG_OPTS', # Vital table!
                          'DLOG_MT_INSTALL_PARMS', # Vital table!
                          #'DLOG_MT_COIN_VAL_TABLE',
#                          'DLOG_MT_NUM_PLAN_TABLE_1', # Non-vital table
#                          'DLOG_MT_NUM_PLAN_TABLE_2', # Non-vital table
                          #'DLOG_MT_MDS_FCONFIG',
                          'DLOG_MT_RATE_TABLE_1', # Vital table!
                          'DLOG_MT_RATE_TABLE_2', # Vital table!
                          'DLOG_MT_RATE_TABLE_3', # Vital table!
                          'DLOG_MT_RATE_TABLE_4', # Vital table!
                          'DLOG_MT_RATE_TABLE_5', # Vital table!
                          ##'DLOG_MT_CALL_SCREEN_LIST_1',
                          ##'DLOG_MT_CALL_SCREEN_LIST_2',
                          ##'DLOG_MT_CALL_SCREEN_LIST_3',
                          ##'DLOG_MT_CALL_SCREEN_LIST_4',
                          ##'DLOG_MT_CALL_SCREEN_LIST_5',
                          ##'DLOG_MT_CALL_SCREEN_LIST_6',
                          ##'DLOG_MT_CALL_SCREEN_LIST_7',
                          ##'DLOG_MT_CALL_SCREEN_LIST_8',
                          ##'DLOG_MT_CALL_SCREEN_LIST_9',
                          ##'DLOG_MT_CALL_SCREEN_LIST_10',
                          ##'DLOG_MT_CALL_SCREEN_LIST_11',
                          ##'DLOG_MT_CALL_SCREEN_LIST_12',
                          ##'DLOG_MT_CALL_SCREEN_LIST_13',
                          ##'DLOG_MT_CALL_SCREEN_LIST_14',
                          ##'DLOG_MT_CALL_SCREEN_LIST_15',
                          ##'DLOG_MT_SCARD_PARM_TABLE',
                          'DLOG_MT_NPA_NXX_TABLE_1_1', # Vital table!
                          'DLOG_MT_NPA_NXX_TABLE_1_2', # Vital table!
                          'DLOG_MT_NPA_NXX_TABLE_1_3', # Vital table!
                          'DLOG_MT_NPA_NXX_TABLE_1_4', # Vital table!
                          'DLOG_MT_END_DATA',
                        ]
    print "pyMM Initialization done."
    print

  def readloop(self):
    if self.__ser.read() == '\x02':
      incoming = []
      # Framenumber
      frameID = self.__ser.read()

      # Framelength
      framelen = self.__ser.read()

      for i in range(0, int(hexlify(framelen), 16)-2):
        incoming.append(self.__ser.read())

      if incoming[-1] != '\x03':
        print "Invalid frame"
        #self.printframe(incoming)
      else:
        #print "Valid frame"

        # Remove CRC1 CRC2 ETC
        incoming = incoming[:-3]

        #Short messages
        if len(incoming) == 0:
          incoming.append(frameID)
          self.printframe(incoming, 'IN')

          if incoming[0] == '\x03': # NCC.H / 3
            print "NCC_C_PKT_MASK - Control byte mask for pkt num\n"
          elif incoming[0] == '\x04': # NCC.H / 4
            print "NCC_C_RE_TRANS - Control byte - re-trans bit\n"
          elif incoming[0] == '\x08' or incoming[0] == '\x09' or incoming[0] == '\x0A' or  incoming[0] == '\x0B': # NCC.H / 8 | 9 | 10 | 11
            #print "ACK-08\n"
            print "ACK-08-09-0A-0B\n"
            #if self.__expectACKsendEOD == True:
            #  self.__expectACKsendEOD = False
            #  self.DLOG_MT_END_DATA()
            #if self.__expectACKsendTRANS == True:
            #  self.__expectACKsendTRANS = False
            #  self.DLOG_MT_TRANS_DATA()
            print "ACK-ACTION: " + self.__expectACKsendWhat
            if self.__expectACKsendWhat == 'EOD':
              self.DLOG_MT_END_DATA()
            elif self.__expectACKsendWhat == 'TRANS':
              self.DLOG_MT_TRANS_DATA()
            elif self.__expectACKsendWhat == 'TABLE':
              self.sendNextTable()
            elif self.__expectACKsendWhat == 'CLRCALL':
              self.clearCall()
            else:
              print "!!! not sending anything !!!"
            if self.__multiTable != True:
              self.__expectACKsendWhat = ''
            self.__multiTable = False
          elif incoming[0] == '\x10': # NCC.H / 16
            print "NCC_C_NACK - Control byte - nack bit\n"
          elif incoming[0] == '\x20': # NCC.H / 32
            print "NCC_C_CLR - Control byte - clr call bit\n"
            self.__ser.close()
            self.__init__(serialport = self.__serialport, baudrate = self.__baudrate, timeout = self.__timeout)
          else:
            print "Unknown Control byte\n"

        # Full length messages
        else:
          #self.__frameID = frameID
          self.__ANI = incoming[:5]
          incoming = incoming[5:]
          self.printframe(incoming, 'IN')

          while len(incoming) > 0:
            if incoming[0] == '\x06': # 6
              print "DLOG_MT_MAINT_REQ - Maintenance action report request"
              print "* OP-code: " + str(int("".join(self.hexlist(incoming[1:3][::-1])), 16)) # 2-1
              print "* PIN-Code: " + "".join(self.hexlist(incoming[3:6]))[:-1] # 3-5
              print
              incoming = incoming[6:]
              self.DLOG_MT_MAINT_ACK(incoming[1:3])
            elif incoming[0] == '\x07': # 7
              print "DLOG_MT_ALARM - Alarm" # 0
              print "* Time: " + self.datetostr(self.hextodate(incoming[1:7])) # 1-6
              print "* Type: " + self.decodealarm(incoming[7]) # 7
              print
              self.DLOG_MT_ALARM_ACK(incoming[7])
              incoming = incoming[8:]
            elif incoming[0] == '\x08': # 8
              print "DLOG_MT_CALL_IN - Terminal call in" # 0
              print
              incoming = incoming[1:]
              #self.DLOG_MT_CALL_IN_PARMS()
            elif incoming[0] == '\x09': # 9
              print "DLOG_MT_CALL_BACK - Terminal call back" # 0
              print
              incoming = incoming[1:]
            elif incoming[0] == '\x0A': # 10
              print "DLOG_MT_TERM_STATUS - Terminal status" # 0
              print "* Serial: " + "".join(self.hexlist(incoming[1:6])) # 1-5
              print "* Telephony: " + hexlify(incoming[6]) # 6 FIXME
              print "* Control: " + hexlify(incoming[7]) # 7 FIXME
              print "* Control Mem: " + hexlify(incoming[8]) # 8 FIXME
              print "* Mechanical: " + hexlify(incoming[9]) # 9 FIXME
              print "* Card Reader: " + hexlify(incoming[10]) # 10 FIXME
              print
              incoming = incoming[11:]
            elif incoming[0] == '\x0D': # 13
              print "DLOG_MT_END_DATA - End of data"
              print
              incoming = incoming[1:]
              self.DLOG_MT_END_DATA(standalone = False)
            elif incoming[0] == '\x0E': # 14
              print "DLOG_MT_TAB_UPD_ACK - Table update acknowledge"
              print "* Terminal received update for table No. " + hexlify(incoming[1])
              print
              incoming = incoming[2:]
              #self.__expectACKsendWhat = 'TABLE'
            elif incoming[0] == '\x24': # 36
              print "DLOG_MT_TIME_SYNC_REQ - Request time_sync"
              print
              incoming = incoming[1:]
              self.DLOG_MT_TIME_SYNC()
            elif incoming[0] == '\x25': # 37
              print "DLOG_MT_PERF_STATS - Performance statistics" # 0
              print "* FIXME Processing of data" # FIXME 1-98
              print
              incoming = incoming[99:]
            elif incoming[0] == '\x26': # 38
              print "DLOG_MT_CASH_BOX_STATUS - Cash box status" # 0
              print "* Time: " + self.datetostr(self.hextodate(incoming[1:7])) # 1-6
              print "* Status: " + hexlify(incoming[7]) #7 FIXME
              print "* Box Number: " +" ".join(self.hexlist(incoming[8:12])) # 8-11 FIXME
              print "* Fill Percentage: " + hexlify(incoming[12]) # 12 FIXME
              print "* Box Amount: " + " ".join(self.hexlist(incoming[13:17])) # 13-16 (16-13?) FIXME
              print "* Coindata ???: " + " ".join(self.hexlist(incoming[17:37])) # 17-36 FIXME
              print "* Spare ???: " + " ".join(self.hexlist(incoming[18:57])) # 18-56 FIXME
              print
              incoming = incoming[57:]
            elif incoming[0] == '\x2C': # 44
              print "DLOG_MT_ATN_REQ_TAB_UPD - Attention req. download tables" # 0
              print "* Reason: " + hexlify(incoming[1]) # 1 FIXME
              print
              incoming = incoming[2:]
              self.DLOG_MT_TABLE_UPD()
              self.__expectACKsendWhat = 'TABLE'
            elif incoming[0] == '\x38': # 56 (Pre-MSR1.7: 48)
              print "DLOG_MT_CALL_STATS - Summary card call statistics" # 0
              print "* Time Start: " + self.datetostr(self.hextodate(incoming[1:7])) # 1-6
              print "* Time Stop: " + self.datetostr(self.hextodate(incoming[7:13])) # 7-12
              print "* Number of local calls: " + "".join(self.hexlist(incoming[13:15])) # 13-14 FIXME
              print "* Number of intera calls: " + "".join(self.hexlist(incoming[15:17])) # 15-16 FIXME
              print "* Number of inter calls: " + "".join(self.hexlist(incoming[17:19])) # 17-18 FIXME
              print "* Number of international calls: " + "".join(self.hexlist(incoming[19:21])) # 19-20 FIXME
              print "* Number of incoming calls: " + "".join(self.hexlist(incoming[21:23])) # 21-22 FIXME
              print "* Number of unanswered calls: " + "".join(self.hexlist(incoming[23:25])) # 23-24 FIXME
              print "* Number of abandoned calls: " + "".join(self.hexlist(incoming[25:27])) # 25-26 FIXME
              print "* Number of operator calls: " + "".join(self.hexlist(incoming[27:29])) # 27-28 FIXME
              print "* Number of 0+ calls: " + "".join(self.hexlist(incoming[29:31])) # 29-30 FIXME
              print "* Number of 1-800 calls: " + "".join(self.hexlist(incoming[31:33])) # 31-32 FIXME
              print "* Number of denied calls: " + "".join(self.hexlist(incoming[33:35])) # 33-34 FIXME
              print "* Number of directory assistance calls: " + "".join(self.hexlist(incoming[35:37])) # 35-36 FIXME
              print "* Number of free calls: " + "".join(self.hexlist(incoming[37:39])) # 37-38 FIXME
              print "* Number of follow on calls: " + "".join(self.hexlist(incoming[39:41])) # 39-40 FIXME
              print "* Total number of POTS calls: " + "".join(self.hexlist(incoming[41:43])) # 41-42 FIXME
              print "* Number of repdialer calls: " + "".join(self.hexlist(incoming[43:45])) # 43-44 FIXME
              print "* Number of repdialer 1 calls: " + "".join(self.hexlist(incoming[45:47])) # 45-46 FIXME
              print "* Number of repdialer 2 calls: " + "".join(self.hexlist(incoming[47:49])) # 47-48 FIXME
              print "* Number of repdialer 3 calls: " + "".join(self.hexlist(incoming[49:51])) # 49-50 FIXME
              print "* Number of repdialer 4 calls: " + "".join(self.hexlist(incoming[51:53])) # 51-52 FIXME
              print "* Number of repdialer 5 calls: " + "".join(self.hexlist(incoming[53:55])) # 53-54 FIXME
              print "* Number of repdialer 6 calls: " + "".join(self.hexlist(incoming[55:57])) # 55-56 FIXME
              print "* Number of repdialer 7 calls: " + "".join(self.hexlist(incoming[57:59])) # 57-58 FIXME
              print "* Number of repdialer 8 calls: " + "".join(self.hexlist(incoming[59:61])) # 59-60 FIXME
              print "* Number of repdialer 9 calls: " + "".join(self.hexlist(incoming[61:63])) # 61-62 FIXME
              print "* Number of repdialer 10 calls: " + "".join(self.hexlist(incoming[63:65])) # 63-64 FIXME
              print "* Total Call Duration: " + "".join(self.hexlist(incoming[65:69])) # 65-68 FIXME
              print "* Total Time off Hook: " + "".join(self.hexlist(incoming[69:73])) # 69-72 FIXME
              print "* Number of feature group B calls: " + "".join(self.hexlist(incoming[73:75])) # 73-74 FIXME
              print "* Number of datajack calls: " + "".join(self.hexlist(incoming[75:77])) # 75-76 FIXME
              print "* Number of 1-8000 billable calls: " + "".join(self.hexlist(incoming[77:79])) # 77-78 FIXME
              print "* Number of completed datajack calls: " + "".join(self.hexlist(incoming[79:81])) # 79-80 FIXME
              print
              incoming = incoming[81:]
            elif incoming[0] == '\x39': # DLOGDEF. H / 57
              print "DLOG_MT_CARRIER_STATS - Summary carrier statistics" # 0
              print "* FIXME Processing of data" # FIXME 1-189
              print
              incoming = incoming[190:]
            elif incoming[0] == '\x3C': # 60
              print "DLOG_MT_SW_VERSION - S/W version" # 0
              print "* Control ROM: " + self.hextostr(incoming[1:8]) # 1-7
              print "* Control Version: " + self.hextostr(incoming[8:12]) # 8-11
              print "* Telephony ROM: " + self.hextostr(incoming[12:19]) # 12-18
              print "* Telephony Version: " + self.hextostr(incoming[19:23]) # 19-22
              print "* Terminal Type: " + hexlify(incoming[23]) # 23
              print "* Validator EEPROM Config ID: " + self.hextostr(incoming[24:28]) # 24-27
              print
              incoming = incoming[28:]
            else:
              print "Unknown DLOG-message\n"
              self.printframe(incoming, "!")
              break

          self.sendACK()
          self.sendQueue()

    return

  #############################################################################
  #                                                                           #
  # DIALOG LAYER FUNCTIONS                                                    #
  #                                                                           #
  #############################################################################
  def DLOG_MT_END_DATA(self, standalone = True): # 13
    outframe = ['\x0D']
    if (standalone == True):
      outframe = self.makeframe(outframe)
      self.sendframe(outframe, "DLOG_MT_END_DATA - End of data")
    else:
      self.addtoqueue(outframe, "DLOG_MT_END_DATA - End of data")
      #self.__expectACKsendWhat = 'NONE'
      self.__expectACKsendWhat = ''

  def DLOG_MT_MAINT_ACK(self, opcode): # 15
    outframe = ['\x0F']
    outframe = outframe + opcode
    self.addtoqueue(outframe, "DLOG_MT_MAINT_ACK - Maintenance acknowledge")

  def DLOG_MT_ALARM_ACK(self, alarmnum): # 16
    outframe = ['\x10']
    outframe.append(alarmnum)
    self.addtoqueue(outframe, "DLOG_MT_ALARM_ACK - Alarm acknowledge")

  def DLOG_MT_TRANS_DATA(self): # 17
    outframe = ['\x11']
    #self.addtoqueue(outframe, "DLOG_MT_TRANS_DATA - Transmit terminal data")
    outframe = self.makeframe(outframe)
    self.sendframe(outframe, "DLOG_MT_TRANS_DATA - Transmit terminal data")

  def DLOG_MT_TABLE_UPD(self): # 18
    outframe = ['\x12']
    #outframe = self.makeframe(outframe)
    #self.sendframe(outframe, "DLOG_MT_TABLE_UPD - Terminal table/data update")
    self.addtoqueue(outframe, "DLOG_MT_TABLE_UPD - Terminal table/data update")

  def DLOG_MT_TIME_SYNC(self): # 20
    outframe = ['\x14']
    outframe.append(chr(datetime.today().year-1900))
    outframe.append(chr(datetime.today().month))
    outframe.append(chr(datetime.today().day))
    outframe.append(chr(datetime.today().hour))
    outframe.append(chr(datetime.today().minute))
    outframe.append(chr(datetime.today().second))
    outframe.append(chr(datetime.today().isoweekday()))
    self.addtoqueue(outframe, "DLOG_MT_TIME_SYNC - Date/time sychronization")
    self.__expectACKsendWhat = 'EOD'

  def DLOG_MT_CARD_TABLE_1(self): # 20-1
    outframe = ['\x16']
    #outframe.extend(['\x40', '\x00', '\x00', '\x49', '\x99', '\x99', '\x04', '\x0A', '\x01', '\x00', '\x00', '\x10', '\x1E', '\x10', '\x2E', '\x11', '\x0E', '\x11', '\x1E', '\x50', '\x1E', '\x50', '\x2E', '\x51', '\x0E', '\x51', '\x1E', '\x00', '\x00', '\x00', '\x00', '\x00', '\xFF',
    # Visa without service codes
    outframe.extend(['\x40', '\x00', '\x00', '\x49', '\x99', '\x99', '\x04', '\x0A', '\x01', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\xFF',
                     '\x51', '\x00', '\x00', '\x55', '\x99', '\x99', '\x04', '\x0A', '\x01', '\x00', '\x00', '\x10', '\x1E', '\x10', '\x2E', '\x11', '\x0E', '\x11', '\x1E', '\x50', '\x1E', '\x50', '\x2E', '\x51', '\x0E', '\x51', '\x1E', '\x00', '\x00', '\x00', '\x00', '\x00', '\xFF',
                     '\x37', '\x00', '\x00', '\x37', '\x99', '\x99', '\x03', '\x0A', '\x01', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\xFF',
                     '\x85', '\x55', '\x00', '\x85', '\x55', '\x99', '\x01', '\x12', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\xFF',
                     '\x89', '\x00', '\x00', '\x89', '\x99', '\x99', '\x02', '\x52', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\xFF',
                     '\x66', '\x00', '\x00', '\x66', '\x00', '\x33', '\x05', '\x12', '\x00', '\x00', '\x05', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\xFF',
                     '\x91', '\x91', '\x00', '\x92', '\x55', '\x16', '\x0A', '\x0E', '\x00', '\x00', '\x00', '\x01', '\xF1', '\xB1', '\x41', '\x41', '\x41', '\xFF', '\x03', '\x45', '\xFF', '\x0F', '\xF0', '\xFF', '\xF0', '\xAB', '\x30', '\x20', '\x20', '\x2F', '\x00', '\x01', '\xFF'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_CARD_TABLE_1 - CARD TABLE - PART 1/3")

  def DLOG_MT_CARD_TABLE_2(self): # 20-2
    outframe = [] # No FrameID necessary
    outframe.extend(['\x90', '\x11', '\x00', '\x92', '\x55', '\x16', '\x0A', '\x0E', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x56', '\x78', '\x9F', '\xFF', '\xFF', '\xFF', '\xFF', '\xFF', '\xAB', '\x2B', '\xAC', '\x28', '\x35', '\x00', '\x01', '\xFF',
                     '\x99', '\x99', '\x00', '\x99', '\x99', '\x00', '\x04', '\x08', '\x01', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\xFF',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_CARD_TABLE_2 - CARD TABLE - PART 2/3")

  def DLOG_MT_CARD_TABLE_3(self): # 20-3
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.addtoqueue(outframe, "DLOG_MT_CARD_TABLE_3 - CARD TABLE - PART 3/3")

  def DLOG_MT_NCC_TERM_PARMS(self): # 21
    '''
    BYTE    msg_type;       /* message type indicator byte  */
    BYTE    term_id[NCC_TERM_SIZE]; /* new terminal id      */
    HEX_TEL datapac_num[NA_LDIST_TEL_NUM_LEN];
    HEX_TEL alt_datapac_num[NA_LDIST_TEL_NUM_LEN];
    '''
    outframe = ['\x15']
    outframe.extend(self.__ANI) # Terminal ANI
    outframe.extend(['\x51', '\x45', '\x55', '\x11', '\x11', '\x00']) # NCC ANI
    outframe.extend(['\x15', '\x19', '\x64', '\x52', '\x31', '\x20']) # NCC Backup ANI
    self.addtoqueue(outframe, "DLOG_MT_NCC_TERM_PARMS - NCC TERMINAL PARAMETERS TABLE")

  def DLOG_MT_NCC_TERM_PARMS_MTR2X(self): # 21
    '''
    DLOG_NCC_TERM_PARMS demo_rom_ncc_term_table = {
        DLOG_MT_NCC_TERM_PARMS,					// BYTE		msg_type

        { 0x51, 0x96, 0x45, 0x23, 0x14 },		// BYTE		term_id[NCC_TERM_SIZE]
        { 0x15, 0x19, 0x64, 0x52, 0x31, 0x20 },	// HEX_TEL	datapac_num[NA_LDIST_TEL_NUM_LEN]
        { 0x15, 0x19, 0x64, 0x52, 0x31, 0x20 },	// HEX_TEL	alt_datapac_num[NA_LDIST_TEL_NUM_LEN]
        { 0x00, 0x00, 0x00, 0x00 },				// HEX_TEL	cad_id[4]
	    { 0x00, 0x00, 0x00, 0x00 },				// HEX_TEL	cpe_id[4]
	    { 0x00, 0x00, 0x00 }					// BYTE		spare_1[3]
    };
    '''
    outframe = ['\x15']
    outframe.extend(['\x51', '\x45', '\x55', '\x22', '\x22']) # Terminal ANI
    #outframe.extend(self.__ANI)
    #outframe.extend(['\x15', '\x19', '\x64', '\x52', '\x31', '\x20']) # NCC ANI
    outframe.extend(['\x51', '\x45', '\x55', '\x11', '\x11', '\x00']) # NCC ANI
    outframe.extend(['\x15', '\x19', '\x64', '\x52', '\x31', '\x20']) # NCC Backup ANI
    outframe.extend(['\x00', '\x00', '\x00', '\x00'])
    outframe.extend(['\x00', '\x00', '\x00', '\x00'])
    outframe.extend(['\x00', '\x00', '\x00'])
    self.addtoqueue(outframe, "DLOG_MT_NCC_TERM_PARMS - NCC TERMINAL PARAMETERS TABLE")
    self.__expectACKsendWhat = 'NONE'
    #outframe = ['\x0D']
    #self.addtoqueue(outframe, "DLOG_MT_END_DATA - End of data")

  def DLOG_MT_FCONFIG_OPTS(self): # 26
    outframe = ['\x1A']
    outframe.extend(['\x01', '\x01', '\x05', '\x07', '\x01', '\x01', '\x00', '\x0F', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x05', '\x00', '\x00', '\x08', '\x08', '\x03', '\x06', '\x05', '\x00',
                     '\x78', '\x00', '\x05', '\x0A', '\x00', '\x2D', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x0E', '\x00', '\x00', '\x0E',
                     '\x05', '\x05', '\x00', '\x01', '\xF4', '\x01', '\xC8', '\x00', '\xE8', '\x03',
                     '\x32', '\x00', '\x32', '\x00', '\x2C', '\x01', '\x00', '\x00', '\x00', '\x00',
                     '\x00'])
    self.addtoqueue(outframe, "DLOG_MT_FCONFIG_OPTS - FEATURE CONFIGURATION TABLE")

  def DLOG_MT_INSTALL_PARMS(self): # 31
    outframe = ['\x1F']
#    outframe.extend(['\x27', '\x27', '\x37', '\x8E', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
    outframe.extend(['\x27', '\x27', '\x37', '\x8E', '\x42', '\x63', '\x54', '\x09', '\x01', '\x00',
                     '\x0A', '\x0A', '\x00', '\x00', '\x2C', '\x01', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.addtoqueue(outframe, "DLOG_MT_INSTALL_PARMS - INSTALLATION PARAMETERS TABLE")

  def DLOG_MT_CALL_IN_PARMS(self): # 35
    outframe = ['\x23']
    outframe.extend(['\x00', '\x00', '\x00', '\x02', '\x00', '\x00', '\x01', '\x00', '\x00', '\x05',
                     '\x00', '\x1E', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.addtoqueue(outframe, "DLOG_MT_CALL_IN_PARMS - TERMINAL CALL-IN PARAMETERS TABLE")

  def DLOG_MT_NUM_PLAN_TABLE_1(self): # 62-1
    outframe = ['\x3E']
    outframe.extend(['\x03', '\x0C', '\x0C', '\x2C', '\x01', '\xC2', '\x01', '\x0B', '\x43', '\x44',
                     '\x0B', '\x0B', '\x0B', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x88',
                     '\x13', '\x00', '\x11', '\x08', '\x00', '\x20', '\x2F', '\x02', '\x01', '\x0A',
                     '\x00', '\x2B', '\x00', '\x20', '\x2F', '\x03', '\x11', '\x11', '\x11', '\x18',
                     '\x00', '\xA4', '\x30', '\x07', '\x01', '\x0A', '\x22', '\x33', '\x10', '\x10',
                     '\xC4', '\x03', '\x0A', '\x01', '\x01', '\x22', '\x2B', '\x33', '\x30', '\x10',
                     '\x88', '\x02', '\x0A', '\x01', '\x18', '\x3F', '\x47', '\x30', '\x10', '\x08',
                     '\x01', '\x0A', '\x3F', '\x00', '\x00', '\x06', '\x30', '\x2F', '\x05', '\x11',
                     '\x11', '\x11', '\x11', '\x11', '\x12', '\x47', '\x47', '\x10', '\x10', '\x44',
                     '\x01', '\x01', '\x2B', '\x50', '\x50', '\x05', '\x31', '\x2F', '\x03', '\x12',
                     '\x11', '\x11', '\x00', '\x00', '\x08', '\x32', '\x43', '\x07', '\x12', '\x11',
                     '\x11', '\x11', '\x11', '\x11', '\x11', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x0A', '\x0A', '\x01', '\x00', '\x01', '\x0A', '\x11', '\x11',
                     '\x11', '\x00', '\x17', '\x11', '\x00', '\x00', '\x0A', '\x01', '\x00', '\x2B',
                     '\x2B', '\x00', '\x00', '\x01', '\x00', '\x1D', '\x31', '\x01', '\x00', '\x0A',
                     '\x00', '\x23', '\x31', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_NUM_PLAN_TABLE_1 - NUMBERING PLAN TABLE - PART 1/2")


  def DLOG_MT_NUM_PLAN_TABLE_2(self): # 62-2
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x81', '\x00', '\x31', '\x00', '\x04', '\x00', '\x12', '\x01', '\x01',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x51', '\x00', '\x42', '\x39', '\x01',
                     '\x00', '\x12', '\x11', '\x11', '\x00', '\x42', '\x00', '\x04', '\x00', '\x11',
                     '\x11', '\x11', '\x11', '\x00', '\x00', '\x00', '\x00', '\x00', '\x12', '\x11',
                     '\x91', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.addtoqueue(outframe, "DLOG_MT_NUM_PLAN_TABLE_2 - NUMBERING PLAN TABLE - PART 2/2")

  def DLOG_MT_RATE_TABLE_1(self): # 73-1
    outframe = ['\x49']
    outframe.extend(['\x59', '\x0B', '\x01', '\x00', '\x00', '\x00',
                     '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00',
                     '\x02', '\xFF', '\xFF', '\x19', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x01', '\x3C', '\x00', '\x05', '\x00', '\x3C', '\x00', '\x05', '\x00',
                     '\x01', '\x3C', '\x00', '\x69', '\x00', '\x3C', '\x00', '\x19', '\x00',
                     '\x01', '\x3C', '\x00', '\xD2', '\x00', '\x3C', '\x00', '\xB4', '\x00',
                     '\x04', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x05', '\x3C', '\x00', '\xF4', '\x01', '\x78', '\x00', '\xA5', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x01', '\x3C', '\x00', '\x2C', '\x01', '\x00', '\x00', '\x0A', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_RATE_TABLE_1 - LCD RATE TABLE - PART 1/5")

  def DLOG_MT_RATE_TABLE_2(self): # 73-2
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_RATE_TABLE_2 - LCD RATE TABLE - PART 2/5")

  def DLOG_MT_RATE_TABLE_3(self): # 73-3
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_RATE_TABLE_3 - LCD RATE TABLE - PART 3/5")

  def DLOG_MT_RATE_TABLE_4(self): # 73-4
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_RATE_TABLE_4 - LCD RATE TABLE - PART 4/5")

  def DLOG_MT_RATE_TABLE_5(self): # 73-5
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', 
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.addtoqueue(outframe, "DLOG_MT_RATE_TABLE_5 - LCD RATE TABLE - PART 5/5")

  def DLOG_MT_NPA_NXX_TABLE_1_1(self): # 74-1
    outframe = ['\x4A']
    outframe.extend(['\x81', '\x9E',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_NPA_NXX_TABLE_1_1 - 1st NPA/NXX table - PART 1/4")

  def DLOG_MT_NPA_NXX_TABLE_1_2(self): # 74-2
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_NPA_NXX_TABLE_1_2 - 1st NPA/NXX table - PART 2/4")

  def DLOG_MT_NPA_NXX_TABLE_1_3(self): # 74-3
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_NPA_NXX_TABLE_1_3 - 1st NPA/NXX table - PART 3/4")

  def DLOG_MT_NPA_NXX_TABLE_1_4(self): # 74-4
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.addtoqueue(outframe, "DLOG_MT_NPA_NXX_TABLE_1_4 - 1st NPA/NXX table - PART 4/4")

  def DLOG_MT_CALL_SCREEN_LIST_1(self): # 92-1
    outframe = ['\x5C']
    outframe.extend(['\x05', '\x07', '\xFF', '\x0A', '\x10', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x05', '\x07', '\xFF', '\x07', '\x51', '\x40', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x05', '\x07', '\xFF', '\x07', '\x43', '\x80', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x05', '\x07', '\xFF', '\x03', '\x70', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x05', '\x07', '\xFF', '\x00', '\x91', '\x10', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_CALL_SCREEN_LIST_1 - Call screen list table update - PART 1/15")


  def DLOG_MT_CALL_SCREEN_LIST_2(self): # 92-2
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_CALL_SCREEN_LIST_2 - Call screen list table update - PART 2/15")

  def DLOG_MT_CALL_SCREEN_LIST_3(self): # 92-3
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_CALL_SCREEN_LIST_3 - Call screen list table update - PART 3/15")

  def DLOG_MT_CALL_SCREEN_LIST_4(self): # 92-4
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_CALL_SCREEN_LIST_4 - Call screen list table update - PART 4/15")

  def DLOG_MT_CALL_SCREEN_LIST_5(self): # 92-5
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_CALL_SCREEN_LIST_5 - Call screen list table update - PART 5/15")

  def DLOG_MT_CALL_SCREEN_LIST_6(self): # 92-6
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_CALL_SCREEN_LIST_6 - Call screen list table update - PART 6/15")

  def DLOG_MT_CALL_SCREEN_LIST_7(self): # 92-7
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_CALL_SCREEN_LIST_7 - Call screen list table update - PART 7/15")

  def DLOG_MT_CALL_SCREEN_LIST_8(self): # 92-8
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_CALL_SCREEN_LIST_8 - Call screen list table update - PART 8/15")

  def DLOG_MT_CALL_SCREEN_LIST_9(self): # 92-9
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_CALL_SCREEN_LIST_9 - Call screen list table update - PART 9/15")

  def DLOG_MT_CALL_SCREEN_LIST_10(self): # 92-10
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_CALL_SCREEN_LIST_10 - Call screen list table update - PART 10/15")

  def DLOG_MT_CALL_SCREEN_LIST_11(self): # 92-11
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_CALL_SCREEN_LIST_11 - Call screen list table update - PART 11/15")

  def DLOG_MT_CALL_SCREEN_LIST_12(self): # 92-12
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_CALL_SCREEN_LIST_12 - Call screen list table update - PART 12/15")

  def DLOG_MT_CALL_SCREEN_LIST_13(self): # 92-13
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_CALL_SCREEN_LIST_13 - Call screen list table update - PART 13/15")

  def DLOG_MT_CALL_SCREEN_LIST_14(self): # 92-14
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.__expectACKsendWhat = 'TABLE'
    self.__multiTable = True
    self.addtoqueue(outframe, "DLOG_MT_CALL_SCREEN_LIST_14 - Call screen list table update - PART 14/15")

  def DLOG_MT_CALL_SCREEN_LIST_15(self): # 92-15
    outframe = [] # No FrameID necessary
    outframe.extend(['\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\xFF', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.addtoqueue(outframe, "DLOG_MT_CALL_SCREEN_LIST_15 - Call screen list table update - PART 15/15")

  def DLOG_MT_SCARD_PARM_TABLE(self): # 93
    outframe = ['\x5D']
    outframe.extend(['\xB9', '\x21', '\x30', '\x53', '\x45', '\x4B', '\xA5', '\x52',
                     '\x0C', '\x9F', '\x14', '\x1B', '\x1C', '\xC4', '\x9E', '\x71',
                     '\x94', '\x5F', '\xCF', '\xE7', '\xAC', '\x1B', '\x80', '\x60',
                     '\x8A', '\x72', '\x23', '\x8E', '\x03', '\x0C', '\x36', '\xB0',
                     '\xF7', '\x3E', '\xA5', '\x8E', '\x98', '\x87', '\xA2', '\x4C',
                     '\x6C', '\xA1', '\xA8', '\xB8', '\x78', '\xF1', '\x7E', '\x70',
                     '\xF1', '\x8F', '\x6B', '\x4E', '\xE5', '\xDF', '\xBD', '\x86',
                     '\x83', '\xB5', '\xE0', '\x09', '\x07', '\x01', '\x81', '\xD9',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',

                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',


                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',

                     '\x00', '\x00',
                     '\x00', '\x00',

                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00',
                     '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00', '\x00'])
    self.addtoqueue(outframe, "DLOG_MT_SCARD_PARM_TABLE - SMART CARD TABLE")

  def DLOG_MT_NPA_SBR_TABLE_1(self): # 150
    outframe = ['\x96']
    outframe.extend(['\x33', '\x33', '\xf3', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x33', '\xf3', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x63', '\x33', '\x73', '\x3f', '\xf3', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x43', '\x33', '\x53', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x93', '\x33', '\x3f', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x33', '\xf3', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x73', '\x3f', '\x3a', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x3f', '\x33', '\x34', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x3f', '\x33', '\x33', '\x33', '\x30', '\x33', '\x33', '\xf3', '\xf3',
                     '\x33', '\x33', '\x33', '\x33', '\x33', '\x3f', '\x33', '\x33', '\x33', '\xf3',
                     '\x38', '\x33', '\x33', '\x33', '\x33', '\xf3', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x3e', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x33', '\xf3', '\x33', '\x33', '\x33', '\xf3', '\x33', '\x3f',
                     '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x3f',
                     '\x3f', '\x33', '\x33', '\x3f', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\xf3', '\x33', '\xf3', '\x33', '\x33', '\x33', '\x3f', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x33', '\x3f', '\x39', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\xd3', '\x33', '\x33', '\xf6', '\xc3', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x33', '\x33'])
    self.addtoqueue(outframe, "DLOG_MT_NPA_SBR_TABLE_1 - NPA set based rating table - PART 1/2")
  
  def DLOG_MT_NPA_SBR_TABLE_2(self): # 150-2
    outframe = [] # No FrameID necessary
    outframe.extend(['\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x3f', '\x33',
                     '\x3f', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x33', '\x33', '\x33', '\xb3', '\x33', '\x33', '\x33', '\x3b',
                     '\x33', '\x33', '\x33', '\x33', '\x33', '\xf3', '\xf3', '\x33', '\x73', '\x33',
                     '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x3f',
                     '\x3c', '\x33', '\x33', '\x33', '\x33', '\x3f', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x3f',
                     '\xe7', '\x33', '\x3f', '\x33', '\x93', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\xf3', '\x3f', '\x33',
                     '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33', '\x33',
                     '\x33', '\x33', '\x33', '\x33', '\x33', '\x33'])
    self.addtoqueue(outframe, "DLOG_MT_NPA_SBR_TABLE_2 - NPA set based rating table - PART 2/2")

  def sendACK(self):
    acks = ['\x08', '\x09', '\x0A', '\x0B']
    outframe = [acks[self.__nextACK]]
    outframe = self.makeframe(outframe, True)
    self.sendframe(outframe, "iter-ACK 08-09-0A-0B")

    self.__nextACK += 1
    if self.__nextACK == 4:
      self.__nextACK = 0

  def clearCall(self):
    outframe = ['\x20']
    outframe = self.makeframe(outframe, True)
    self.sendframe(outframe, "CLEAR CALL 0x20")

  #############################################################################
  #                                                                           #
  # HELPER FUNCTIONS                                                          #
  #                                                                           #
  #############################################################################
  def sendNextTable(self):
      methodToCall = getattr(self, self.__tableOrder.pop(0))
      methodToCall()
      self.sendQueue()

  def addtoqueue(self, frame, description):
    self.__outqueue = self.__outqueue + frame
    self.__outqueuedesc.append(description)

  def sendQueue(self):
    if (self.__outqueue != []):
      outframe = self.makeframe(self.__outqueue)
      self.sendframe(outframe, ", ".join(self.__outqueuedesc))
      #self.__expectACKsendTRANS = True
      if self.__expectACKsendWhat == '':
        #self.__expectACKsendWhat = 'TRANS'
        #self.__expectACKsendWhat = 'CLRCALL'
        pass        
      self.__outqueue = []
      self.__outqueuedesc = []
    else:
      #print "OutQueue empty - sending TRANS (FIXME)"
      #self.DLOG_MT_TRANS_DATA()
      print "__tableOrder length: " + str(len(self.__tableOrder))
      if len(self.__tableOrder) > 0:
        print "OutQueue empty - sending next Table (FIXME)"
        self.sendNextTable()
        if (len(self.__tableOrder) > 0) and (self.__expectACKsendWhat != 'TABLE'):
          print "clearing ACK #1"
          self.__expectACKsendWhat = ''
      else:
        print "OutQueue empty - not doing anything"
        #self.__expectACKsendWhat = 'EOD'
        

  def makeframe(self, inframe, shortframe = False):
    outframe = ['\x02'] # STX

    if shortframe == True:
      outframe.extend(inframe) # provided content-data
      outframe.append('\xFF') # Framelength-placeholder
    else:
      outframe.append(self.__frameID)
      outframe.append('\xFF') # Framelength-placeholder
      outframe.extend(self.__ANI)
      outframe.extend(inframe) # provided content-data
      self.newframe()

    outframe[2] = chr(len(outframe) + 2) # framelen = frame so far + 2 crc (ETX ignored!)

    outframe = outframe + self.crc(outframe)
    outframe.append('\x03') # ETX

    return outframe

  def sendframe(self, frame, function = ""):
    self.printframe(frame, 'OUT')
    if function != "":
      print(function + '\n')
    self.__ser.write(bytearray(frame))

  def printframe(self, frame, direction = "IN"):
    colorend = '\033[0m'

    if direction == "IN":
      color = '\033[93m'
    elif direction == "OUT":
      color = '\033[92m'
    else:
      color = colorend

    print color + direction + ": " + " ".join(self.hexlist(frame)) + colorend

  def hexlist(self, frame):
    newframe = []
    for i in frame:
      newframe.append(hexlify(i))

    return newframe

  def crc(self, frame):
    crc16 = crcmod.predefined.mkCrcFun('crc-16')

    crcstring = "".join(self.hexlist(frame))
    crc = "{0:#0{1}x}".format(crc16(unhexlify(crcstring)), 6)

    return [unhexlify(crc[4:]), unhexlify(crc[2:-2])]

  #def newframe(self):
  #  frameID = ord(self.__frameID)
  #  frameID += 1
  #  self.__frameID = chr(frameID)

  def newframe(self):
    frames = ['\x00', '\x01', '\x02', '\x03']

    self.__nextFrame += 1
    if self.__nextFrame == 4:
      self.__nextFrame = 0

    self.__frameID = frames[self.__nextFrame]

  def hextostr(self, hexlist):
    return "".join(hexlist)

  def hextodate(self, hexlist):
    # A date is always 6 bytes long!
    while len(hexlist) < 6:
      hexlist.append('\x00')
    timestamp = [int(hexlify(i), 16) for i in hexlist]
    timestamp[0] += 1900
    timestamp = " ".join([str(i) for i in timestamp])
    timestamp = time.strptime(timestamp, "%Y %m %d %H %M %S")
    return timestamp

  def datetostr(self, date):
    return time.strftime("%a, %d %b %Y %H:%M:%S", date)

  def decodealarm(self, alarm, isHex = True):
    alarms = { 0: 'Handset discontinuity',
               1: 'Telephony board not responding',
               8: 'Power fail',
               9: 'Display not responding',
              10: 'Voice synthesis not responding',
              12: 'Card Reader blocked',
              16: 'CDR checksum error',
              17: 'Statistics checksum error',
              18: 'Terminal table checksum error',
              19: 'Other data checksum error',
              20: 'CDR list full',
              21: 'Bad EEPROM',
              22: 'Control microprocessor RAM contents lost',
              23: 'Control microprocessor RAM defective',
              24: 'Station access cover open',
              25: 'Stuck button',
              26: 'Set removal',
              27: 'Cash box threshbold met',
              28: 'Coin box cover opened',
              29: 'Cash box removed',
              30: 'Cash box full',
              31: 'Validator jam',
              32: 'Escrow jam',
              33: 'Validator hardware failure',
              34: 'Central office (CO) line check failure',
              35: 'Dialog failure',
              99: 'Un-alarm'}

    if isHex == True:
      alarm = int(hexlify(alarm), 16)

    return str(alarm) + ": " + alarms.get(alarm, "ERROR - UNKNOWN ALARM")
