import tkinter as tk
from tkinter import *
from tweet_collector import *
from datetime import datetime
from datetime import timedelta


class Application(tk.Frame):
    def __init__(self, master, ck, cs, at, ats, bt, sid, ts, d, fn):
        super().__init__(master)

        self.sub_ids = sid

        self.texts = []
        self.labels = []
        self.images = []
        self.panels = []

        self.index = 0
        self.master = master
        self.width_window = 600
        self.height_window = 10 + (len(self.sub_ids) + 1) * 30

        self.image_status_on = PhotoImage(file="images/on.png")
        self.image_status_off = PhotoImage(file="images/off.png")

        c_key = ck
        c_secret = cs
        a_token = at
        a_token_secret = ats
        b_token = bt

        self.sub_ids = sid
        self.sub_keys = list(self.sub_ids.keys())
        self.time_stamp = ts
        self.delay = d
        self.file_name = fn

        master.title('Tweet collector')
        master.geometry(str(self.width_window) + "x" + str(self.height_window))
        self.canvas = Canvas(root, width=self.width_window, height=self.height_window)
        self.canvas.pack()

        self.selected_item = 0
        self.fill_app()

        self.tc = TweetCollector(c_key, c_secret, a_token, a_token_secret, b_token,
                                 self.sub_ids, self.file_name, self.delay)
        self.last_update = datetime.utcnow()
        self.paint_process()

    def update(self):
        self.canvas.delete("all")
        self.paint_process()

        if datetime.utcnow() - self.last_update >= timedelta(seconds=self.time_stamp):
            self.tc.update()
            self.last_update = datetime.utcnow()
            for index, text in enumerate(self.texts):
                new_date = " " + str(self.tc.get_dates(index))[:-1].replace("T", " : ") + " | " \
                           + self.sub_ids[self.sub_keys[index]]
                self.texts[index].set(new_date)
                if self.tc.statuses[index]:
                    self.panels[index].config(image=self.image_status_on)
                else:
                    self.panels[index].config(image=self.image_status_off)


        app.after(30, app.update)

    def paint_process(self):
        percent_finished = (datetime.utcnow() - self.last_update).total_seconds() / self.time_stamp

        self.canvas.create_rectangle(0, self.height_window - 20, self.width_window,
                                     self.height_window, fill='#434343', outline="")
        self.canvas.create_rectangle(0, self.height_window - 20, self.width_window * percent_finished,
                                     self.height_window, fill='#767676', outline="")

        self.canvas.create_rectangle(0, 10 + self.tc.actual_id * 30, 20,
                                     10 + self.tc.actual_id * 30 + 19, fill='#000000', outline="")

    def fill_app(self):
        actual_date = str(datetime.utcnow().strftime(" %Y-%m-%dT%H:%M:%SZ")[:-1].replace("T", " : "))
        for i in range(len(self.sub_ids)):
            english_text = tk.StringVar()
            english_text.set(actual_date + " | " + self.sub_ids[self.sub_keys[i]])
            english_label = tk.Label(
                self.master, textvariable=english_text, font=('bold', 15), anchor='center')
            english_label.place(x=45, y=5 + i * 30)

            image_status = self.image_status_on
            panel = tk.Label(self.master, image=image_status)
            panel.place(x=20, y=5 + i * 30)
            self.panels.append(panel)
            self.images.append(image_status)
            self.texts.append(english_text)
            self.labels.append(english_label)



file_name, time_stamp, delay = None, None, None
file = open('files/config.txt', 'r')
for line in file.readlines():
    exec(line.strip())

##############################################################################
file_name = 'files/tweet_db.json' if file_name is None else file_name
time_stamp = 10 if time_stamp is None else time_stamp
delay = 30 if delay is None else delay
##############################################################################

root = tk.Tk()
app = Application(root, c_key, c_secret, a_token, a_token_secret, b_token, sub_ids, time_stamp, delay, file_name)
app.after(30, app.update)
app.mainloop()
