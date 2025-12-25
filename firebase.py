import firebase_admin
from firebase_admin import credentials, db
import json
import time
from datetime import datetime

# Konfigurasi Firebase
class FirebaseRealtimeDB:
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
            
        except Exception as e:
            print(f"❌ Error inisialisasi Firebase: {e}")
            raise
    
    def send_data(self, path, data):
        """
        Mengirim data ke path tertentu
        
        Args:
            path: Path di database (contoh: 'sensors/temperature')
            data: Data yang akan dikirim (dictionary)
        """
        try:
            # Tambahkan timestamp jika belum ada
            if 'timestamp' not in data:
                data['timestamp'] = datetime.now().isoformat()
            
            # Kirim data ke Firebase
            ref = self.db.child(path)
            ref.push(data)  # Menggunakan push() untuk membuat ID unik
            # Atau gunakan set() untuk menimpa data:
            # ref.set(data)
            
            print(f"✅ Data berhasil dikirim ke path: {path}")
            print(f"📊 Data: {json.dumps(data, indent=2)}")
            return True
            
        except Exception as e:
            print(f"❌ Error mengirim data: {e}")
            return False
    
    def send_sensor_data(self, sensor_type, value, unit="", location=""):
        """
        Fungsi khusus untuk mengirim data sensor
        
        Args:
            sensor_type: Jenis sensor (temperature, humidity, dll)
            value: Nilai sensor
            unit: Satuan (Celsius, %, dll)
            location: Lokasi sensor
        """
        data = {
            'value': value,
            'unit': unit,
            'sensor_type': sensor_type,
            'location': location,
            'timestamp': datetime.now().isoformat()
        }
        
        path = f"sensors/{sensor_type}"
        return self.send_data(path, data)
    
    def send_multiple_data(self, path, data_list):
        """
        Mengirim beberapa data sekaligus
        
        Args:
            path: Path di database
            data_list: List berisi dictionary data
        """
        try:
            ref = self.db.child(path)
            for data in data_list:
                if 'timestamp' not in data:
                    data['timestamp'] = datetime.now().isoformat()
                ref.push(data)
            
            print(f"✅ {len(data_list)} data berhasil dikirim ke path: {path}")
            return True
            
        except Exception as e:
            print(f"❌ Error mengirim multiple data: {e}")
            return False

# Contoh penggunaan
def main():
    # Konfigurasi - GANTI DENGAN KONFIGURASI ANDA
    SERVICE_ACCOUNT_KEY = "D:/Python Project/Randi UNP/SerialAccesKey.json"  # File service account dari Firebase
    DATABASE_URL = "https://python-data-b88bb-default-rtdb.firebaseio.com/"    # URL database Anda
    
    # Contoh data
    sensor_readings = [
        {"temperature": 25.5, "humidity": 60},
        {"temperature": 26.0, "humidity": 58},
        {"temperature": 24.8, "humidity": 62}
    ]
    
    try:
        # Inisialisasi koneksi
        firebase = FirebaseRealtimeDB(SERVICE_ACCOUNT_KEY, DATABASE_URL)
        
        print("\n📤 Mengirim data ke Firebase...")
        
        # Contoh 1: Mengirim data sensor tunggal
        print("\n1. Mengirim data sensor tunggal:")
        firebase.send_sensor_data(
            sensor_type="temperature",
            value=25.5,
            unit="°C",
            location="Ruangan A"
        )
        
        # Contoh 2: Mengirim data ke path tertentu
        print("\n2. Mengirim data ke path 'users':")
        user_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
            "city": "Jakarta"
        }
        firebase.send_data("users", user_data)
        
        # Contoh 3: Mengirim multiple data
        print("\n3. Mengirim multiple data:")
        readings = []
        for i, reading in enumerate(sensor_readings):
            data = {
                "reading_id": i + 1,
                "temperature": reading["temperature"],
                "humidity": reading["humidity"],
                "status": "normal"
            }
            readings.append(data)
        
        firebase.send_multiple_data("sensor_readings", readings)
        
        # Contoh 4: Simulasi data sensor real-time
        print("\n4. Simulasi data sensor real-time (5 detik):")
        for i in range(5):
            # Data simulasi
            temp = 25 + (i * 0.5)
            humid = 60 - (i * 1)
            
            firebase.send_sensor_data(
                sensor_type="temperature",
                value=temp,
                unit="°C",
                location="Greenhouse"
            )
            
            firebase.send_sensor_data(
                sensor_type="humidity",
                value=humid,
                unit="%",
                location="Greenhouse"
            )
            
            print(f"📈 Iterasi {i+1}: Temperature={temp}°C, Humidity={humid}%")
            time.sleep(1)  # Tunggu 1 detik
        
        print("\n🎉 Semua data berhasil dikirim!")
        
    except FileNotFoundError:
        print("❌ File service account key tidak ditemukan!")
        print("💡 Pastikan path file benar dan file JSON ada")
    except Exception as e:
        print(f"❌ Terjadi error: {e}")

# Program alternatif yang lebih sederhana
def simple_example():
    """
    Contoh program yang lebih sederhana
    """
    import firebase_admin
    from firebase_admin import credentials, db
    from datetime import datetime
    
    # Setup Firebase
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://your-project-id.firebaseio.com/'
    })
    
    # Reference ke database
    ref = db.reference()
    
    # Data yang akan dikirim
    data = {
        "message": "Hello Firebase!",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "active"
    }
    
    # Kirim data
    ref.child("messages").push(data)
    print("✅ Data sederhana berhasil dikirim!")

if __name__ == "__main__":
    print("🚀 Program Pengirim Data Firebase")
    print("=" * 40)
    
    # Jalankan contoh utama
    main()
    
    # Atau jalankan contoh sederhana
    # simple_example()