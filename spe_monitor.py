"""
spe_monitor.py — Monitoring temps réel + commandes SPE Expert 1.3K-FA
v2 : rendement PA, puissance consommée, boutons de contrôle
Style Station Master — Consolas, palette sombre
ON5AM — hamanalyst.org
"""

import tkinter as tk
import threading
import queue
import time
import sys

from spe_expert import SPEExpert, AmpStatus

# ─── Configuration ────────────────────────────────────────────────────────────

PORT     = 'COM3'
BAUDRATE = 115200
POLL_MS  = 500

# Palette Station Master
BG       = '#1a1a2e'
BG2      = '#16213e'
BG3      = '#0f3460'
BG_BTN   = '#0d2137'
FG       = '#e0e0e0'
GREEN    = '#00ff88'
YELLOW   = '#ffd700'
RED      = '#ff4444'
CYAN     = '#00bfff'
ORANGE   = '#ff8c00'

FONT_TITLE  = ('Consolas', 13, 'bold')
FONT_LABEL  = ('Consolas',  11)
FONT_VALUE  = ('Consolas', 14, 'bold')
FONT_SMALL  = ('Consolas',  10)
FONT_MODE   = ('Consolas', 12, 'bold')
FONT_BTN    = ('Consolas',  10, 'bold')


# ─── Widget barre de puissance ────────────────────────────────────────────────

class PowerBar(tk.Canvas):
    MAX_W = 1300

    def __init__(self, parent, **kwargs):
        super().__init__(parent, height=18, bg=BG2,
                         highlightthickness=1, highlightbackground='#333366',
                         **kwargs)
        self._value = 0
        self.bind('<Configure>', lambda e: self._draw())

    def set(self, watts: int):
        self._value = max(0, min(watts, self.MAX_W))
        self._draw()

    def _draw(self):
        self.delete('all')
        w, h = self.winfo_width(), self.winfo_height()
        if w < 2:
            return
        self.create_rectangle(0, 0, w, h, fill='#111122', outline='')
        ratio = self._value / self.MAX_W
        bar_w = int(w * ratio)
        if bar_w > 0:
            color = GREEN if ratio < 0.5 else (YELLOW if ratio < 0.75 else RED)
            self.create_rectangle(0, 2, bar_w, h - 2, fill=color, outline='')
        self.create_text(w // 2, h // 2,
                         text=f'{self._value} W', fill=FG,
                         font=FONT_SMALL, anchor='center')
        for mark in [250, 500, 750, 1000, 1250]:
            x = int(w * mark / self.MAX_W)
            self.create_line(x, h - 4, x, h, fill='#444466')


# ─── Widget barre SWR ────────────────────────────────────────────────────────

class SWRBar(tk.Canvas):

    def __init__(self, parent, **kwargs):
        super().__init__(parent, height=14, bg=BG2,
                         highlightthickness=1, highlightbackground='#333366',
                         **kwargs)
        self._value = 1.0
        self.bind('<Configure>', lambda e: self._draw())

    def set(self, swr: float):
        self._value = max(1.0, min(swr, 3.5))
        self._draw()

    def _draw(self):
        self.delete('all')
        w, h = self.winfo_width(), self.winfo_height()
        if w < 2:
            return
        self.create_rectangle(0, 0, w, h, fill='#111122', outline='')
        ratio = (self._value - 1.0) / 2.5
        bar_w = int(w * ratio)
        if bar_w > 0:
            # Rouge dès 1.6:1 — seuil alarme ampli
            color = GREEN if self._value < 1.4 else (YELLOW if self._value < 1.6 else RED)
            self.create_rectangle(0, 2, bar_w, h - 2, fill=color, outline='')
        self.create_text(w // 2, h // 2,
                         text=f'{self._value:.2f}', fill=FG,
                         font=FONT_SMALL, anchor='center')


# ─── Fenêtre principale ───────────────────────────────────────────────────────

class SPEMonitor(tk.Tk):

    def __init__(self, port=PORT, baudrate=BAUDRATE):
        super().__init__()
        self.title('SPE Expert 1.3K-FA — Monitor')
        self.configure(bg=BG)
        self.resizable(False, False)

        self._port     = port
        self._baudrate = baudrate
        self._amp      = None
        self._running  = False
        self._thread   = None
        self._cmd_q    = queue.Queue()

        self._build_ui()
        self._start_polling()
        self.protocol('WM_DELETE_WINDOW', self._on_close)

    # ── Construction UI ───────────────────────────────────────────────────────

    def _build_ui(self):

        # Header
        hdr = tk.Frame(self, bg=BG3, pady=4)
        hdr.pack(fill='x')
        tk.Label(hdr, text='SPE EXPERT 1.3K-FA', font=FONT_TITLE,
                 bg=BG3, fg=CYAN).pack(side='left', padx=10)
        self._lbl_mode = tk.Label(hdr, text='● CONNECTING…',
                                  font=FONT_MODE, bg=BG3, fg=YELLOW)
        self._lbl_mode.pack(side='right', padx=10)

        body = tk.Frame(self, bg=BG, padx=8, pady=6)
        body.pack(fill='both')

        # Ligne 1 : infos statiques
        row1 = tk.Frame(body, bg=BG2, padx=6, pady=4)
        row1.pack(fill='x', pady=(0, 4))
        self._lbl_band  = self._make_kv(row1, 'Bande',   '---', CYAN)
        self._lbl_ant   = self._make_kv(row1, 'Ant TX',  '---', FG)
        self._lbl_bank  = self._make_kv(row1, 'Bank',    '-',   FG)
        self._lbl_input = self._make_kv(row1, 'Input',   '-',   FG)
        self._lbl_plvl  = self._make_kv(row1, 'Niveau',  '---', YELLOW)

        # Ligne 2 : Puissance OUT
        row2 = tk.Frame(body, bg=BG, pady=2)
        row2.pack(fill='x')
        tk.Label(row2, text='Puissance OUT', font=FONT_LABEL,
                 bg=BG, fg=CYAN, width=14, anchor='w').pack(side='left')
        self._bar_power = PowerBar(row2)
        self._bar_power.pack(side='left', fill='x', expand=True, padx=(4, 0))

        # Ligne 3 : SWR ATU
        row3 = tk.Frame(body, bg=BG, pady=2)
        row3.pack(fill='x')
        tk.Label(row3, text='SWR (ATU)', font=FONT_LABEL,
                 bg=BG, fg=CYAN, width=14, anchor='w').pack(side='left')
        self._bar_swr_atu = SWRBar(row3)
        self._bar_swr_atu.pack(side='left', fill='x', expand=True, padx=(4, 0))

        # Ligne 4 : SWR antenne
        row4 = tk.Frame(body, bg=BG, pady=2)
        row4.pack(fill='x')
        tk.Label(row4, text='SWR (Ant)', font=FONT_LABEL,
                 bg=BG, fg=CYAN, width=14, anchor='w').pack(side='left')
        self._bar_swr_ant = SWRBar(row4)
        self._bar_swr_ant.pack(side='left', fill='x', expand=True, padx=(4, 0))

        # Ligne 5 : PA tension / courant / température
        row5 = tk.Frame(body, bg=BG2, padx=6, pady=5)
        row5.pack(fill='x', pady=(6, 2))
        self._lbl_vpa  = self._make_kv(row5, 'PA Tension',  '-- V',  GREEN)
        self._lbl_ipa  = self._make_kv(row5, 'PA Courant',  '-- A',  GREEN)
        self._lbl_temp = self._make_kv(row5, 'Temp heatsk', '--°C',  GREEN)

        # Ligne 6 : Puissance consommée + rendement
        row6 = tk.Frame(body, bg=BG2, padx=6, pady=5)
        row6.pack(fill='x', pady=(0, 4))
        self._lbl_pin  = self._make_kv(row6, 'P consommée', '--- W', ORANGE)
        self._lbl_eff  = self._make_kv(row6, 'Rendement',   '-- %',  ORANGE)
        self._lbl_pdis = self._make_kv(row6, 'P dissipée',  '--- W', YELLOW)

        # Ligne 7 : Warnings / Alarms
        row7 = tk.Frame(body, bg=BG, pady=3)
        row7.pack(fill='x')
        self._lbl_warn  = tk.Label(row7, text='Warning : aucun',
                                   font=FONT_SMALL, bg=BG, fg=GREEN, anchor='w')
        self._lbl_warn.pack(side='left', padx=2)
        self._lbl_alarm = tk.Label(row7, text='Alarm : aucune',
                                   font=FONT_SMALL, bg=BG, fg=GREEN, anchor='e')
        self._lbl_alarm.pack(side='right', padx=2)

        # Boutons de commande
        btn_frame = tk.Frame(self, bg=BG3, pady=5)
        btn_frame.pack(fill='x')

        buttons = [
            ('OPERATE',   'OPERATE',      CYAN),
            ('TUNE',      'TUNE',         GREEN),
            ('POWER',     'POWER',        YELLOW),
            ('INPUT',     'INPUT',        FG),
            ('ANTENNE',   'ANTENNA',      FG),
            ('BACKLIGHT', 'BACKLIGHT_ON', '#8888aa'),
        ]
        for label, cmd, color in buttons:
            tk.Button(
                btn_frame, text=label, font=FONT_BTN,
                bg=BG_BTN, fg=color,
                activebackground='#1a3a5c', activeforeground=color,
                relief='flat', padx=8, pady=3, cursor='hand2',
                command=lambda c=cmd: self._send_cmd(c),
            ).pack(side='left', padx=3)

        # Status bar
        self._lbl_status = tk.Label(
            self, text=f'Port : {self._port}',
            font=FONT_SMALL, bg='#111122', fg='#666688',
            anchor='w', padx=6)
        self._lbl_status.pack(fill='x', side='bottom')

        self.geometry('540x430')

    def _make_kv(self, parent, label, init_val, color):
        f = tk.Frame(parent, bg=parent['bg'], padx=8)
        f.pack(side='left')
        tk.Label(f, text=label, font=FONT_SMALL,
                 bg=parent['bg'], fg='#8888aa').pack(anchor='w')
        lbl = tk.Label(f, text=init_val, font=FONT_VALUE,
                       bg=parent['bg'], fg=color)
        lbl.pack(anchor='w')
        return lbl

    # ── Commandes ─────────────────────────────────────────────────────────────

    def _send_cmd(self, cmd: str):
        self._cmd_q.put(cmd)

    # ── Thread de polling ─────────────────────────────────────────────────────

    def _start_polling(self):
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def _poll_loop(self):
        try:
            self._amp = SPEExpert(self._port, self._baudrate)
            self._amp.connect()
            self.after(0, lambda: self._set_status('Connecté', GREEN))
        except Exception as e:
            self.after(0, lambda: self._set_status(f'Erreur connexion : {e}', RED))
            return

        while self._running:
            # Commandes en attente (boutons)
            while not self._cmd_q.empty():
                cmd = self._cmd_q.get_nowait()
                try:
                    ok = self._amp.send_key(cmd)
                    msg = f'CMD {cmd} → {"OK" if ok else "ACK?"}'
                    self.after(0, lambda m=msg: self._set_status(m, CYAN))
                    time.sleep(0.15)
                except Exception as e:
                    self.after(0, lambda: self._set_status(f'Erreur cmd : {e}', RED))

            # Polling statut
            try:
                st = self._amp.get_status()
                if st:
                    self.after(0, lambda s=st: self._update_ui(s))
                else:
                    self.after(0, lambda: self._set_status('Pas de réponse', YELLOW))
            except Exception as e:
                self.after(0, lambda: self._set_status(f'Erreur : {e}', RED))
                break

            time.sleep(POLL_MS / 1000)

    # ── Mise à jour UI ────────────────────────────────────────────────────────

    def _update_ui(self, st: AmpStatus):

        # Header
        if st.rx_tx == 'TX':
            self._lbl_mode.config(text=f'● TX — {st.mode}', fg=RED)
        elif st.mode == 'Operate':
            self._lbl_mode.config(text='● OPERATE', fg=GREEN)
        else:
            self._lbl_mode.config(text='○ STANDBY', fg=YELLOW)

        # Ligne 1
        self._lbl_band.config(text=st.band)
        self._lbl_ant.config(text=st.tx_ant)
        self._lbl_bank.config(text=st.bank)
        self._lbl_input.config(text=str(st.input_port))
        self._lbl_plvl.config(text=st.power_level)

        # Barres
        self._bar_power.set(st.out_power_w)
        self._bar_swr_atu.set(st.swr_atu if st.swr_atu > 0 else 1.0)
        self._bar_swr_ant.set(st.swr_ant if st.swr_ant > 0 else 1.0)

        # PA
        self._lbl_vpa.config(text=f'{st.vpa:.1f} V',
                             fg=GREEN if st.vpa > 0 else FG)
        self._lbl_ipa.config(text=f'{st.ipa:.1f} A',
                             fg=GREEN if st.ipa > 0 else FG)
        temp_color = RED if st.temp_c > 60 else (YELLOW if st.temp_c > 45 else GREEN)
        self._lbl_temp.config(text=f'{st.temp_c}°C', fg=temp_color)

        # Rendement
        p_in  = st.vpa * st.ipa
        p_out = st.out_power_w
        p_dis = max(0.0, p_in - p_out)

        if p_in > 5:
            eff = (p_out / p_in) * 100
            self._lbl_pin.config(text=f'{p_in:.0f} W')
            self._lbl_eff.config(
                text=f'{eff:.0f} %',
                fg=GREEN if eff > 50 else (YELLOW if eff > 30 else ORANGE))
            self._lbl_pdis.config(text=f'{p_dis:.0f} W')
            status_sfx = (f'{p_out} W  |  SWR {st.swr_ant:.2f}  |  '
                          f'{st.temp_c}°C  |  η {eff:.0f}%')
        else:
            self._lbl_pin.config(text='--- W')
            self._lbl_eff.config(text='-- %', fg=ORANGE)
            self._lbl_pdis.config(text='--- W')
            status_sfx = 'STANDBY'

        # Warnings / Alarms
        self._lbl_warn.config(
            text=f'Warning : {st.warning or "aucun"}',
            fg=YELLOW if st.warning else GREEN)
        self._lbl_alarm.config(
            text=f'Alarm : {st.alarm or "aucune"}',
            fg=RED if st.alarm else GREEN)

        self._set_status(f'Port : {self._port}  |  {st.band}  |  {status_sfx}')

    def _set_status(self, msg, color='#666688'):
        self._lbl_status.config(text=msg, fg=color)

    # ── Fermeture ─────────────────────────────────────────────────────────────

    def _on_close(self):
        self._running = False
        if self._amp:
            self._amp.disconnect()
        self.destroy()


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = sys.argv[1] if len(sys.argv) > 1 else PORT
    try:
        app = SPEMonitor(port=port)
        app.mainloop()
    except KeyboardInterrupt:
        pass