# -*- coding: utf-8 -*-

import os
import subprocess
import time
import re
import wx
import threading

in_process = False

class myframe(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent)
        self.SetTitle('Batch Converter')
        self.pnl = wx.Panel(self)
        self.l_bit_rate = wx.StaticBox(self.pnl, label='target bitrate')
        self.t_bit_rate = wx.TextCtrl(self.pnl)
        self.l_extention = wx.StaticBox(self.pnl, label='source extention')
        self.t_extention = wx.TextCtrl(self.pnl)
        self.b1 = wx.Button(self.pnl, label='start')
        self.b1.Bind(wx.EVT_BUTTON, self.onStart)
        self.l_progress = wx.StaticBox(self.pnl, label='وضعیت')
        self.t_progress = wx.TextCtrl(self.pnl, size=(300, -1), style=wx.TE_READONLY|wx.TE_MULTILINE)
        self.total_progress = wx.Gauge(self, range=100)
        self.file_progress = wx.Gauge(self, range=100)
    
    def onStart(self, e):
        global convert_thread, in_process
        if not in_process:
            extention = self.t_extention.GetValue()
            if extention != '':
                info = get_information(os.getcwd(), extention)
                print(info['total'])
                bit_rate = self.t_bit_rate.GetValue()
                if bit_rate != '':
                    bit_rate = '-b:a ' + bit_rate + 'K '
                convert_thread = threading.Thread(target=convert, args=(info, bit_rate,))
                convert_thread.daemon = True
                convert_thread.start()
                in_process = True

app = wx.App()
frm = myframe(None)
frm.Show()

def convert_to_seconds(time_string):
    time_object = time.strptime(time_string, '%H:%M:%S')
    return time_object.tm_hour*3600 + time_object.tm_min*60 + time_object.tm_sec

def get_information(path, extention):
    mp3_details = {}
    total_convert_length = 0
    total_files = 0
    files_converted = 0
    for x in os.walk(path):
        if path+'\\result' in x[0]:
            continue
        for y in x[2]:
            if re.search(extention+'$', y):
                SourcePath = x[0]
                SourceFile = SourcePath + '\\' + y
                DestPath = SourcePath.replace(path, path+'\\result')
                DestFile = DestPath + '\\' + y.replace(extention, 'mp3')
                mp3_details[SourceFile] = {'SourceFile': SourceFile, 'DestFile': DestFile, 'DestPath': DestPath}
                command = 'ffmpeg -i \"' + SourceFile + '\"'
                output = subprocess.run(command, capture_output=True, text=True)
                time_string = re.search('Duration: .{2}:.{2}:.{2}', output.stderr).group().replace('Duration: ', '')
                Duration = convert_to_seconds(time_string)
                mp3_details[SourceFile]['Duration'] = Duration
                total_convert_length += Duration
                total_files += 1
    mp3_details['total'] = {'total files': total_files, 'total convert length': total_convert_length}
    return mp3_details

def convert(mp3_details, bit_rate):
    global in_process
    total_converted = 0
    total_files = mp3_details['total']['total files']
    files_converted = 0
    frm.file_progress.SetValue(0)
    frm.total_progress.SetValue(0)
    for mp3 in mp3_details.keys():
        if mp3 == 'total':
            continue
        file_progress = total_progress = 0
        timer = last_timer = time.perf_counter()
        item = mp3_details[mp3]
        if not os.path.exists(item['DestPath']):
            os.makedirs(item['DestPath'])
        command = 'ffmpeg -i \"' + item['SourceFile'] + '\" ' + bit_rate + '-y \"' + item['DestFile'] + '\"'
        result = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        status = ''
        total_seconds = item['Duration']
        while result.poll() is None:
            if len(status) > 0 and status[-1] == '\r':
                time_converted = re.search('time=.{2}:.{2}:.{2}', status)
                if time_converted:
                    time_string = time_converted.group().replace('time=', '')
                    file_progress = convert_to_seconds(time_string) * 100 // item['Duration']
                    total_progress = (total_converted + convert_to_seconds(time_string))*100//mp3_details['total']['total convert length']
                    frm.file_progress.SetValue(file_progress)
                    frm.total_progress.SetValue(total_progress)
                    frm.t_progress.SetValue('در حال تبدیل فایل ' + str(files_converted+1) + ' از ' + str(total_files) + '، ' + str(total_progress) + '%')
                    timer = time.perf_counter()
                status = ''
            try:
                status += result.stdout.read(1).decode('utf-8')
            except UnicodeDecodeError:
                pass
        total_converted += item['Duration']
        files_converted += 1
    in_process = False

app.MainLoop()