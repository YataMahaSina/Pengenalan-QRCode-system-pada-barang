import cv2
import numpy as np
import time
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime

class FirebaseManager:
    def __init__(self, credential_path, database_url):
        """
        Inisialisasi koneksi Firebase
        
        Args:
            credential_path: Path ke file service account key (JSON)
            database_url: URL database Firebase
        """
        try:
            # Inisialisasi Firebase hanya sekali
            if not firebase_admin._apps:
                # Load credential dari file
                cred = credentials.Certificate(credential_path)
                # Inisialisasi app dengan database URL
                firebase_admin.initialize_app(cred, {
                    'databaseURL': database_url
                })
            
            print("✅ Firebase berhasil diinisialisasi")
            self.db = db.reference()
            self.setup_database_structure()
            
        except Exception as e:
            print(f"❌ Error inisialisasi Firebase: {e}")
            # Jika Firebase gagal, tetap jalankan program tanpa Firebase
            self.db = None
    
    def setup_database_structure(self):
        """Setup struktur database awal jika belum ada"""
        if not self.db:
            return
            
        try:
            # Inisialisasi struktur jika belum ada
            initial_data = {
                'barang_masuk': {
                    'total': 0,
                    'history': {}
                },
                'barang_keluar': {
                    'total': 0,
                    'history': {}
                },
                'ringkasan': {
                    'total_masuk': 0,
                    'total_keluar': 0,
                    'sisa_barang': 0,
                    'last_update': datetime.now().isoformat()
                }
            }
            
            # Cek apakah database sudah ada data
            existing_data = self.db.get()
            if not existing_data:
                self.db.set(initial_data)
                print("✅ Struktur database diinisialisasi")
            else:
                print("✅ Database sudah memiliki struktur")
                
        except Exception as e:
            print(f"⚠ Peringatan setup database: {e}")
    
    def send_barang_masuk(self, qr_data):
        """Mengirim data barang masuk ke Firebase"""
        if not self.db:
            return False
            
        try:
            timestamp = datetime.now()
            timestamp_str = timestamp.isoformat()
            
            # Data untuk history
            history_data = {
                'qr_data': qr_data,
                'waktu': timestamp_str,
                'mode': 'masuk'
            }
            
            # Kirim ke history
            history_ref = self.db.child('barang_masuk').child('history')
            history_ref.push(history_data)
            
            # Update total barang masuk
            total_ref = self.db.child('barang_masuk').child('total')
            current_total = total_ref.get() or 0
            total_ref.set(current_total + 1)
            
            # Update ringkasan
            self.update_ringkasan()
            
            print(f"✅ Data masuk dikirim ke Firebase: {qr_data}")
            return True
            
        except Exception as e:
            print(f"❌ Error mengirim data masuk: {e}")
            return False
    
    def send_barang_keluar(self, qr_data):
        """Mengirim data barang keluar ke Firebase"""
        if not self.db:
            return False
            
        try:
            timestamp = datetime.now()
            timestamp_str = timestamp.isoformat()
            
            # Data untuk history
            history_data = {
                'qr_data': qr_data,
                'waktu': timestamp_str,
                'mode': 'keluar'
            }
            
            # Kirim ke history
            history_ref = self.db.child('barang_keluar').child('history')
            history_ref.push(history_data)
            
            # Update total barang keluar
            total_ref = self.db.child('barang_keluar').child('total')
            current_total = total_ref.get() or 0
            total_ref.set(current_total + 1)
            
            # Update ringkasan
            self.update_ringkasan()
            
            print(f"✅ Data keluar dikirim ke Firebase: {qr_data}")
            return True
            
        except Exception as e:
            print(f"❌ Error mengirim data keluar: {e}")
            return False
    
    def update_ringkasan(self):
        """Update data ringkasan di Firebase"""
        if not self.db:
            return
            
        try:
            # Ambil total masuk dan keluar
            total_masuk_ref = self.db.child('barang_masuk').child('total')
            total_keluar_ref = self.db.child('barang_keluar').child('total')
            
            total_masuk = total_masuk_ref.get() or 0
            total_keluar = total_keluar_ref.get() or 0
            sisa_barang = total_masuk - total_keluar
            
            # Update ringkasan
            ringkasan_data = {
                'total_masuk': total_masuk,
                'total_keluar': total_keluar,
                'sisa_barang': sisa_barang,
                'last_update': datetime.now().isoformat()
            }
            
            self.db.child('ringkasan').set(ringkasan_data)
            
        except Exception as e:
            print(f"❌ Error update ringkasan: {e}")
    
    def reset_database(self):
        """Reset semua data di database"""
        if not self.db:
            return False
            
        try:
            # Reset ke struktur awal
            initial_data = {
                'barang_masuk': {
                    'total': 0,
                    'history': {}
                },
                'barang_keluar': {
                    'total': 0,
                    'history': {}
                },
                'ringkasan': {
                    'total_masuk': 0,
                    'total_keluar': 0,
                    'sisa_barang': 0,
                    'last_update': datetime.now().isoformat()
                }
            }
            
            self.db.set(initial_data)
            print("✅ Database berhasil direset")
            return True
            
        except Exception as e:
            print(f"❌ Error reset database: {e}")
            return False

class QRCodeDetector:
    def __init__(self, firebase_credential_path, firebase_database_url):
        # Inisialisasi Firebase Manager
        self.firebase = FirebaseManager(firebase_credential_path, firebase_database_url)
        
        # Inisialisasi detektor QR code
        self.qr_detector = cv2.QRCodeDetector()
        
        # Status untuk tracking benda
        self.object_status = {}
        
        # Mode tracking: 'masuk' atau 'keluar'
        self.tracking_mode = 'masuk'  # Default mode masuk
        
        # Counter untuk jumlah barang
        self.count_masuk = 0
        self.count_keluar = 0
        
        # History untuk mencegah deteksi berulang dalam waktu singkat
        self.detection_history = {}
        
        # Warna untuk visualisasi
        self.COLORS = {
            'masuk': (0, 255, 0),      # Hijau untuk barang masuk
            'keluar': (0, 0, 255),     # Merah untuk barang keluar
            'info': (255, 255, 255),   # Putih untuk informasi
            'mode': (255, 200, 0),     # Orange untuk mode aktif
            'warning': (0, 255, 255),  # Kuning untuk peringatan
            'bg_dark': (30, 30, 30),   # Warna background gelap
            'bg_panel': (40, 40, 60),  # Warna panel
            'bg_highlight': (60, 60, 80) # Warna highlight
        }
        
        # Parameter tracking
        self.min_detection_gap = 0.5  # Minimal 0.5 detik antara deteksi QR yang sama
        self.display_time = 3.0  # Tampilkan selama 3 detik
        
    def decode_qr(self, frame):
        """Mendeteksi dan mendecode QR code dari frame"""
        try:
            # Deteksi QR code
            data, bbox, _ = self.qr_detector.detectAndDecode(frame)
            
            if data and bbox is not None and data.strip() != "":
                # Konversi bbox ke integer
                bbox = bbox.astype(int)
                return data.strip(), bbox
        except Exception as e:
            pass
        
        return None, None
    
    def can_detect_qr(self, qr_data, timestamp):
        """Cek apakah QR code boleh dideteksi lagi"""
        if not qr_data:
            return False
            
        if qr_data not in self.detection_history:
            return True
            
        last_detected = self.detection_history[qr_data]['last_detected']
        time_diff = timestamp - last_detected
        
        if time_diff > self.min_detection_gap:
            return True
            
        return False
    
    def process_qr(self, qr_data, bbox, timestamp):
        """Proses QR code berdasarkan mode tracking"""
        if not qr_data or not self.can_detect_qr(qr_data, timestamp):
            return False
        
        # Update history deteksi
        self.detection_history[qr_data] = {
            'last_detected': timestamp,
            'mode': self.tracking_mode
        }
        
        # Cek apakah QR sudah ada di object_status
        if qr_data in self.object_status:
            # Update hanya bbox, jangan reset timer
            self.object_status[qr_data]['bbox'] = bbox.copy()
            self.object_status[qr_data]['last_update'] = timestamp
            self.object_status[qr_data]['mode'] = self.tracking_mode
            updated = False
        else:
            # Tambahkan QR baru ke object_status
            self.object_status[qr_data] = {
                'mode': self.tracking_mode,
                'first_seen': timestamp,
                'last_update': timestamp,
                'bbox': bbox.copy(),
                'display_time': self.display_time
            }
            updated = True
        
        # Update counter berdasarkan mode dan kirim ke Firebase
        history_key = f"{qr_data}_{self.tracking_mode}"
        if history_key not in self.detection_history:
            if self.tracking_mode == 'masuk':
                self.count_masuk += 1
                print(f"📥 BARANG MASUK: {qr_data}")
                # Kirim ke Firebase
                self.firebase.send_barang_masuk(qr_data)
            else:
                self.count_keluar += 1
                print(f"📤 BARANG KELUAR: {qr_data}")
                # Kirim ke Firebase
                self.firebase.send_barang_keluar(qr_data)
            
            self.detection_history[history_key] = timestamp
        
        return updated
    
    def update_display_status(self, timestamp):
        """Update dan hapus status yang sudah expired"""
        qrs_to_remove = []
        
        for qr_data, info in list(self.object_status.items()):
            time_since_first_seen = timestamp - info['first_seen']
            
            if time_since_first_seen > info['display_time']:
                qrs_to_remove.append(qr_data)
        
        for qr_data in qrs_to_remove:
            del self.object_status[qr_data]
            
            if qr_data in self.detection_history:
                time_diff = timestamp - self.detection_history[qr_data]['last_detected']
                if time_diff > self.min_detection_gap * 3:
                    del self.detection_history[qr_data]
    
    def draw_detection(self, frame, qr_data, bbox, mode):
        """Menggambar bounding box dan informasi pada frame"""
        color = self.COLORS[mode]
        
        # Gambar bounding box
        n = len(bbox[0])
        for i in range(n):
            cv2.line(frame, tuple(bbox[0][i]), tuple(bbox[0][(i+1) % n]), color, 3)
        
        # Gambar titik sudut
        for point in bbox[0]:
            cv2.circle(frame, tuple(point), 6, (255, 255, 255), -1)
        
        # Hitung posisi untuk teks
        box_center_x = int(np.mean([p[0] for p in bbox[0]]))
        box_center_y = int(np.mean([p[1] for p in bbox[0]]))
        
        # Potong teks jika terlalu panjang
        display_text = qr_data[:15] + "..." if len(qr_data) > 15 else qr_data
        
        # Background untuk teks
        text = f"{display_text}"
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
        
        # Posisi teks di atas bounding box
        text_x = box_center_x - text_size[0] // 2
        text_y = box_center_y - 15
        
        # Background box untuk teks (rounded corners)
        padding = 5
        cv2.rectangle(frame, 
                     (text_x - padding, text_y - text_size[1] - padding),
                     (text_x + text_size[0] + padding, text_y + padding),
                     color, -1)
        
        # Border untuk text box
        cv2.rectangle(frame, 
                     (text_x - padding, text_y - text_size[1] - padding),
                     (text_x + text_size[0] + padding, text_y + padding),
                     (255, 255, 255), 1)
        
        # Teks QR data
        cv2.putText(frame, text, (text_x, text_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame
    
    def draw_control_panel_right(self, frame):
        """Menggambar panel kontrol di kanan atas dengan desain modern"""
        height, width = frame.shape[:2]
        
        # Panel utama di kanan (350px width)
        panel_width = 350
        panel_x = width - panel_width
        panel_height = height
        
        # Background utama panel
        cv2.rectangle(frame, (panel_x, 0), (width, panel_height), 
                     self.COLORS['bg_dark'], -1)
        
        # Garis pemisah
        cv2.line(frame, (panel_x, 0), (panel_x, panel_height), 
                (100, 100, 120), 2)
        
        # Header Panel
        header_height = 50
        cv2.rectangle(frame, (panel_x, 0), (width, header_height), 
                     self.COLORS['bg_panel'], -1)
        
        # Judul Aplikasi dengan indikator Firebase yang lebih sederhana
        title = "QR TRACKING SYSTEM"
        title_size = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
        title_x = panel_x + (panel_width - title_size[0]) // 2
        
        # Indikator status Firebase - lebih sederhana tanpa teks tambahan
        firebase_color = (0, 255, 0) if self.firebase.db else (0, 0, 255)
        
        # Gambar lingkaran indikator kecil di pojok kiri header
        indicator_radius = 8
        indicator_x = panel_x + 20
        indicator_y = 25
        
        # Lingkaran luar
        cv2.circle(frame, (indicator_x, indicator_y), indicator_radius, firebase_color, -1)
        
        # Lingkaran dalam untuk efek glow
        cv2.circle(frame, (indicator_x, indicator_y), indicator_radius - 2, (255, 255, 255), 1)
        
        # Judul aplikasi
        cv2.putText(frame, title, (title_x, 35), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, self.COLORS['info'], 2)
        
        y_offset = 70
        
        # ==================== PANEL MODE AKTIF ====================
        mode_panel_height = 90
        cv2.rectangle(frame, 
                     (panel_x + 10, y_offset), 
                     (panel_x + panel_width - 10, y_offset + mode_panel_height),
                     self.COLORS['bg_panel'], -1)
        
        cv2.putText(frame, "MODE AKTIF", (panel_x + 20, y_offset + 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLORS['info'], 1)
        
        mode_text = self.tracking_mode.upper()
        mode_color = self.COLORS['masuk'] if self.tracking_mode == 'masuk' else self.COLORS['keluar']
        
        # Mode indicator
        mode_bg_x = panel_x + panel_width - 140
        mode_bg_width = 120
        mode_bg_height = 50
        
        cv2.rectangle(frame, 
                     (mode_bg_x, y_offset + 15),
                     (mode_bg_x + mode_bg_width, y_offset + 15 + mode_bg_height),
                     self.COLORS['bg_highlight'], -1)
        
        cv2.rectangle(frame, 
                     (mode_bg_x, y_offset + 15),
                     (mode_bg_x + mode_bg_width, y_offset + 15 + mode_bg_height),
                     mode_color, 2)
        
        # Hitung ukuran teks
        mode_font_scale = 0.9
        mode_thickness = 2
        mode_size = cv2.getTextSize(mode_text, cv2.FONT_HERSHEY_SIMPLEX, mode_font_scale, mode_thickness)[0]
        
        # Adjust font scale jika teks terlalu besar
        while mode_size[0] > (mode_bg_width - 20) and mode_font_scale > 0.5:
            mode_font_scale -= 0.1
            mode_size = cv2.getTextSize(mode_text, cv2.FONT_HERSHEY_SIMPLEX, mode_font_scale, mode_thickness)[0]
        
        # Posisi teks di tengah box
        mode_text_x = mode_bg_x + (mode_bg_width - mode_size[0]) // 2
        mode_text_y = y_offset + 15 + (mode_bg_height + mode_size[1]) // 2
        
        cv2.putText(frame, mode_text, (mode_text_x, mode_text_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, mode_font_scale, mode_color, mode_thickness)
        
        y_offset += mode_panel_height + 15
        
        # ==================== PANEL COUNTER ====================
        counter_panel_height = 120
        cv2.rectangle(frame, 
                     (panel_x + 10, y_offset), 
                     (panel_x + panel_width - 10, y_offset + counter_panel_height),
                     self.COLORS['bg_panel'], -1)
        
        cv2.putText(frame, "STATISTIK BARANG", (panel_x + 20, y_offset + 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLORS['info'], 1)
        
        # Counter Masuk
        masuk_bg_x = panel_x + 20
        masuk_width = (panel_width - 50) // 2
        masuk_height = 70
        
        cv2.rectangle(frame, 
                     (masuk_bg_x, y_offset + 40),
                     (masuk_bg_x + masuk_width, y_offset + 40 + masuk_height),
                     (30, 60, 30), -1)
        
        cv2.rectangle(frame, 
                     (masuk_bg_x, y_offset + 40),
                     (masuk_bg_x + masuk_width, y_offset + 40 + masuk_height),
                     self.COLORS['masuk'], 2)
        
        # Teks "MASUK"
        masuk_label = "MASUK"
        masuk_label_size = cv2.getTextSize(masuk_label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0]
        masuk_label_x = masuk_bg_x + (masuk_width - masuk_label_size[0]) // 2
        cv2.putText(frame, masuk_label, (masuk_label_x, y_offset + 65),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 255, 200), 1)
        
        # Angka counter Masuk
        masuk_count = str(self.count_masuk)
        
        # Tentukan ukuran font yang sesuai
        masuk_font_scale = 1.4
        masuk_thickness = 2
        masuk_count_size = cv2.getTextSize(masuk_count, cv2.FONT_HERSHEY_SIMPLEX, masuk_font_scale, masuk_thickness)[0]
        
        # Adjust font scale jika teks terlalu besar
        while masuk_count_size[0] > (masuk_width - 20) and masuk_font_scale > 0.5:
            masuk_font_scale -= 0.1
            masuk_count_size = cv2.getTextSize(masuk_count, cv2.FONT_HERSHEY_SIMPLEX, masuk_font_scale, masuk_thickness)[0]
        
        # Posisi angka
        masuk_count_x = masuk_bg_x + (masuk_width - masuk_count_size[0]) // 2
        masuk_count_y = y_offset + 40 + masuk_height - 10
        
        cv2.putText(frame, masuk_count, (masuk_count_x, masuk_count_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, masuk_font_scale, self.COLORS['masuk'], masuk_thickness)
        
        # Counter Keluar
        keluar_bg_x = masuk_bg_x + masuk_width + 10
        
        cv2.rectangle(frame, 
                     (keluar_bg_x, y_offset + 40),
                     (keluar_bg_x + masuk_width, y_offset + 40 + masuk_height),
                     (60, 30, 30), -1)
        
        cv2.rectangle(frame, 
                     (keluar_bg_x, y_offset + 40),
                     (keluar_bg_x + masuk_width, y_offset + 40 + masuk_height),
                     self.COLORS['keluar'], 2)
        
        # Teks "KELUAR"
        keluar_label = "KELUAR"
        keluar_label_size = cv2.getTextSize(keluar_label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0]
        keluar_label_x = keluar_bg_x + (masuk_width - keluar_label_size[0]) // 2
        cv2.putText(frame, keluar_label, (keluar_label_x, y_offset + 65),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 200), 1)
        
        # Angka counter Keluar
        keluar_count = str(self.count_keluar)
        
        # Tentukan ukuran font yang sesuai
        keluar_font_scale = 1.4
        keluar_thickness = 2
        keluar_count_size = cv2.getTextSize(keluar_count, cv2.FONT_HERSHEY_SIMPLEX, keluar_font_scale, keluar_thickness)[0]
        
        # Adjust font scale jika teks terlalu besar
        while keluar_count_size[0] > (masuk_width - 20) and keluar_font_scale > 0.5:
            keluar_font_scale -= 0.1
            keluar_count_size = cv2.getTextSize(keluar_count, cv2.FONT_HERSHEY_SIMPLEX, keluar_font_scale, keluar_thickness)[0]
        
        # Posisi angka
        keluar_count_x = keluar_bg_x + (masuk_width - keluar_count_size[0]) // 2
        keluar_count_y = y_offset + 40 + masuk_height - 10
        
        cv2.putText(frame, keluar_count, (keluar_count_x, keluar_count_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, keluar_font_scale, self.COLORS['keluar'], keluar_thickness)
        
        y_offset += counter_panel_height + 15
        
        # ==================== PANEL INFORMASI SISTEM ====================
        info_panel_height = 120
        cv2.rectangle(frame, 
                     (panel_x + 10, y_offset), 
                     (panel_x + panel_width - 10, y_offset + info_panel_height),
                     self.COLORS['bg_panel'], -1)
        
        cv2.putText(frame, "INFORMASI SISTEM", (panel_x + 20, y_offset + 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLORS['info'], 1)
        
        # QR Aktif
        active_qrs = len(self.object_status)
        cv2.putText(frame, f"QR Aktif: {active_qrs}", (panel_x + 30, y_offset + 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 255), 1)
        
        # Waktu Deteksi
        cv2.putText(frame, f"Durasi: {self.display_time}s", (panel_x + 30, y_offset + 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 255, 200), 1)
        
        # Firebase Status (dipindahkan ke panel informasi sistem)
        firebase_status = "Firebase: AKTIF" if self.firebase.db else "Firebase: OFFLINE"
        firebase_color = (0, 255, 0) if self.firebase.db else (0, 0, 255)
        cv2.putText(frame, firebase_status, (panel_x + 30, y_offset + 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, firebase_color, 1)
        
        # Status Sisa
        sisa = self.count_masuk - self.count_keluar
        status_color = self.COLORS['masuk'] if sisa >= 0 else self.COLORS['keluar']
        status_text = f"Sisa: {abs(sisa)}" if sisa != 0 else "Seimbang"
        cv2.putText(frame, status_text, (panel_x + 30, y_offset + 110), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 1)
        
        y_offset += info_panel_height + 15
        
        # ==================== PANEL KONTROL ====================
        control_panel_height = 200
        cv2.rectangle(frame, 
                     (panel_x + 10, y_offset), 
                     (panel_x + panel_width - 10, y_offset + control_panel_height),
                     self.COLORS['bg_panel'], -1)
        
        cv2.putText(frame, "KONTROL KEYBOARD", (panel_x + 20, y_offset + 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLORS['info'], 1)
        
        # Tombol-tombol dengan desain
        controls = [
            ("M", "Mode Masuk", self.COLORS['masuk']),
            ("K", "Mode Keluar", self.COLORS['keluar']),
            ("R", "Reset Counter", (200, 200, 100)),
            ("C", "Clear History", (200, 200, 100)),
            ("F", "Reset Firebase", (255, 100, 100)),
            ("Q", "Keluar", (200, 200, 200))
        ]
        
        for i, (key, desc, color) in enumerate(controls):
            control_y = y_offset + 50 + (i * 25)
            
            # Key box
            key_box_x = panel_x + 30
            cv2.rectangle(frame, 
                         (key_box_x, control_y - 15),
                         (key_box_x + 25, control_y + 5),
                         self.COLORS['bg_highlight'], -1)
            
            cv2.rectangle(frame, 
                         (key_box_x, control_y - 15),
                         (key_box_x + 25, control_y + 5),
                         color, 1)
            
            cv2.putText(frame, key, (key_box_x + 8, control_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            # Description
            cv2.putText(frame, desc, (key_box_x + 40, control_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.COLORS['info'], 1)
        
        y_offset += control_panel_height + 15
        
        # ==================== PANEL QR TERDETEKSI ====================
        if self.object_status:
            qr_panel_height = min(200, 30 + len(self.object_status) * 25)
            cv2.rectangle(frame, 
                         (panel_x + 10, y_offset), 
                         (panel_x + panel_width - 10, y_offset + qr_panel_height),
                         self.COLORS['bg_panel'], -1)
            
            cv2.putText(frame, "BARANG TERDETEKSI", (panel_x + 20, y_offset + 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLORS['info'], 1)
            
            current_time = time.time()
            qr_y = y_offset + 50
            
            for i, (qr_data, info) in enumerate(list(self.object_status.items())[:6]):  # Maks 6 item
                if qr_y + 25 > y_offset + qr_panel_height - 10:
                    break
                    
                time_since_first_seen = current_time - info['first_seen']
                time_left = max(0, info['display_time'] - time_since_first_seen)
                
                mode = info['mode']
                color = self.COLORS[mode]
                
                # Potong teks
                display_text = qr_data[:12] + "..." if len(qr_data) > 12 else qr_data
                
                # Bullet point
                cv2.circle(frame, (panel_x + 25, qr_y - 5), 3, color, -1)
                
                # Data QR
                qr_text = f"{display_text} [{mode.upper()[:1]}] ({time_left:.0f}s)"
                cv2.putText(frame, qr_text, (panel_x + 35, qr_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.45, self.COLORS['info'], 1)
                
                qr_y += 25
        
        return frame
    
    def clear_detection_history(self):
        """Clear detection history agar QR bisa dideteksi lagi"""
        self.detection_history.clear()
        self.object_status.clear()
        print("History deteksi dan status telah dibersihkan")

def main():
    # Konfigurasi Firebase - GANTI DENGAN KONFIGURASI ANDA
    FIREBASE_CREDENTIAL = "D:/Python Project/Randi UNP/SerialAccesKey.json"
    FIREBASE_DATABASE_URL = "https://python-data-b88bb-default-rtdb.firebaseio.com/"
    
    # Inisialisasi detektor dengan Firebase
    detector = QRCodeDetector(FIREBASE_CREDENTIAL, FIREBASE_DATABASE_URL)
    
    # Buka webcam
    cap = cv2.VideoCapture(0)
    
    # Set resolusi kamera
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    # Coba tingkatkan FPS
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    print("=" * 50)
    print("SISTEM TRACKING BARANG QR CODE DENGAN FIREBASE")
    print("=" * 50)
    print("\nPETUNJUK PENGGUNAAN:")
    print("M - Mode MASUK (hijau) - Scan barang masuk")
    print("K - Mode KELUAR (merah) - Scan barang keluar")
    print("R - Reset semua counter")
    print("C - Clear history deteksi")
    print("F - Reset database Firebase")
    print("Q - Keluar dari program")
    print("\nMode default: MASUK")
    print("Setiap QR ditampilkan selama 3 detik")
    print("Data otomatis dikirim ke Firebase saat QR terdeteksi")
    print("=" * 50)
    
    last_mode_change = time.time()
    last_detection_time = 0
    
    # FPS counter
    fps_start_time = time.time()
    fps_frame_count = 0
    fps = 0
    
    while True:
        # Baca frame dari kamera
        ret, frame = cap.read()
        if not ret:
            print("Gagal membaca frame dari kamera")
            break
        
        # Mirror frame untuk tampilan yang lebih natural
        frame = cv2.flip(frame, 1)
        
        # Salin frame untuk output
        output_frame = frame.copy()
        
        # Hitung FPS
        fps_frame_count += 1
        if time.time() - fps_start_time >= 1.0:
            fps = fps_frame_count
            fps_frame_count = 0
            fps_start_time = time.time()
        
        # Dapatkan timestamp
        current_time = time.time()
        
        # Deteksi QR code
        qr_data, bbox = detector.decode_qr(frame)
        
        # Proses QR code jika terdeteksi
        if qr_data and bbox is not None:
            if current_time - last_detection_time > 0.1:
                success = detector.process_qr(qr_data, bbox, current_time)
                if success:
                    last_detection_time = current_time
        
        # Update status display
        detector.update_display_status(current_time)
        
        # Gambar bounding box untuk QR yang masih aktif
        for qr_data, info in list(detector.object_status.items()):
            if 'bbox' in info:
                output_frame = detector.draw_detection(output_frame, qr_data, info['bbox'], info['mode'])
        
        # Gambar panel kontrol di kanan
        output_frame = detector.draw_control_panel_right(output_frame)
        
        # Tampilkan FPS di kiri bawah
        cv2.putText(output_frame, f"FPS: {fps}", (20, output_frame.shape[0] - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, detector.COLORS['info'], 1)
        
        # Tampilkan status kamera di kiri bawah
        cv2.putText(output_frame, "KAMERA AKTIF", (20, output_frame.shape[0] - 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Tampilkan pesan mode change di tengah bawah
        if current_time - last_mode_change < 2.0:
            mode_text = f"MODE: {detector.tracking_mode.upper()}"
            text_size = cv2.getTextSize(mode_text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)[0]
            
            text_x = (output_frame.shape[1] - 350 - text_size[0]) // 2  # Tengah area kamera
            text_y = output_frame.shape[0] - 30
            
            # Background glow effect
            for i in range(3, 0, -1):
                alpha = 0.3 / i
                overlay = output_frame.copy()
                cv2.rectangle(overlay, 
                             (text_x - 10*i, text_y - text_size[1] - 5*i),
                             (text_x + text_size[0] + 10*i, text_y + 5*i),
                             (0, 0, 0), -1)
                output_frame = cv2.addWeighted(overlay, alpha, output_frame, 1-alpha, 0)
            
            # Main background
            mode_color = detector.COLORS['masuk'] if detector.tracking_mode == 'masuk' else detector.COLORS['keluar']
            cv2.rectangle(output_frame, 
                         (text_x - 10, text_y - text_size[1] - 5),
                         (text_x + text_size[0] + 10, text_y + 5),
                         (20, 20, 20), -1)
            
            cv2.rectangle(output_frame, 
                         (text_x - 10, text_y - text_size[1] - 5),
                         (text_x + text_size[0] + 10, text_y + 5),
                         mode_color, 2)
            
            cv2.putText(output_frame, mode_text, (text_x, text_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, mode_color, 2)
        
        # Tampilkan frame
        cv2.imshow('QR Tracking System - Kamera Live + Panel Kontrol + Firebase', output_frame)
        
        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q') or key == ord('Q'):
            break
        elif key == ord('m') or key == ord('M'):
            detector.tracking_mode = 'masuk'
            last_mode_change = current_time
            print(f"[{time.strftime('%H:%M:%S')}] Mode diubah: MASUK")
        elif key == ord('k') or key == ord('K'):
            detector.tracking_mode = 'keluar'
            last_mode_change = current_time
            print(f"[{time.strftime('%H:%M:%S')}] Mode diubah: KELUAR")
        elif key == ord('r') or key == ord('R'):
            detector.count_masuk = 0
            detector.count_keluar = 0
            print(f"[{time.strftime('%H:%M:%S')}] Semua counter direset")
        elif key == ord('c') or key == ord('C'):
            detector.clear_detection_history()
            print(f"[{time.strftime('%H:%M:%S')}] History deteksi dibersihkan")
        elif key == ord('f') or key == ord('F'):
            if detector.firebase.db:
                if detector.firebase.reset_database():
                    detector.count_masuk = 0
                    detector.count_keluar = 0
                    print(f"[{time.strftime('%H:%M:%S')}] Database Firebase berhasil direset")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] Gagal reset database Firebase")
    
    # Release resources
    cap.release()
    cv2.destroyAllWindows()
    
    # Tampilkan ringkasan akhir
    print("\n" + "=" * 50)
    print("RINGKASAN AKHIR")
    print("=" * 50)
    print(f"Total barang MASUK: {detector.count_masuk}")
    print(f"Total barang KELUAR: {detector.count_keluar}")
    
    if detector.count_masuk > detector.count_keluar:
        sisa = detector.count_masuk - detector.count_keluar
        print(f"\n📊 SISA BARANG DI GUDANG: {sisa}")
    elif detector.count_keluar > detector.count_masuk:
        lebih = detector.count_keluar - detector.count_masuk
        print(f"\n⚠  PERINGATAN: Barang keluar lebih banyak {lebih}")
    else:
        print(f"\n✓ STOK SEIMBANG: Masuk = Keluar")
    
    print("\n📤 Data telah dikirim ke Firebase:")
    print("   - Barang Masuk: di path 'barang_masuk/history'")
    print("   - Barang Keluar: di path 'barang_keluar/history'")
    print("   - Ringkasan: di path 'ringkasan'")
    print("=" * 50)

if __name__ == "__main__":
    main()