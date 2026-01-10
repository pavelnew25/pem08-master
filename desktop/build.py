"""
Скрипт для сборки desktop приложения в .exe
"""

import PyInstaller.__main__
import sys
from pathlib import Path

print("=" * 60)
print("🔨 СБОРКА DESKTOP ПРИЛОЖЕНИЯ")
print("=" * 60)
print()

# Проверяем PyInstaller
try:
    import PyInstaller
    print(f"📦 Проверка PyInstaller...")
    print(f"   ✓ PyInstaller {PyInstaller.__version__}")
    print()
except ImportError:
    print("❌ PyInstaller не установлен!")
    print("Установите: pip install pyinstaller")
    sys.exit(1)

# Параметры сборки
app_name = "CompetitorMonitor"
main_script = "main.py"

# Дополнительные файлы (только те что есть)
datas = [
    ('gemini_client.py', '.'),
    ('parser.py', '.'),
    ('styles.py', '.'),
]

# Скрытые импорты
hidden_imports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'google.generativeai',
    'selenium',
    'PIL',
]

print(f"🚀 Запуск сборки: {app_name}.exe")
print("-" * 60)

# Запуск PyInstaller
PyInstaller.__main__.run([
    main_script,
    f'--name={app_name}',
    '--onefile',
    '--windowed',
    '--clean',
    *[f'--add-data={src};{dst}' for src, dst in datas],
    *[f'--hidden-import={imp}' for imp in hidden_imports],
])

print()
print("=" * 60)
print("✅ СБОРКА ЗАВЕРШЕНА")
print(f"📁 Файл: dist/{app_name}.exe")
print("=" * 60)
