INFO:     Will watch for changes in these directories: ['D:\\PHYTON\\PROJECTS\\CURSOR\\pem08-master']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [1316] using StatReload
Process SpawnProcess-1:
Traceback (most recent call last):
  File "C:\Program Files\Python314\Lib\multiprocessing\process.py", line 320, in _bootstrap
    self.run()
    ~~~~~~~~^^
  File "C:\Program Files\Python314\Lib\multiprocessing\process.py", line 108, in run
    self._target(*self._args, **self._kwargs)
    ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\PHYTON\PROJECTS\CURSOR\pem08-master\venv\Lib\site-packages\uvicorn\_subprocess.py", line 80, in subprocess_started
    target(sockets=sockets)
    ~~~~~~^^^^^^^^^^^^^^^^^
  File "D:\PHYTON\PROJECTS\CURSOR\pem08-master\venv\Lib\site-packages\uvicorn\server.py", line 67, in run
    return asyncio_run(self.serve(sockets=sockets), loop_factory=self.config.get_loop_factory())     
  File "C:\Program Files\Python314\Lib\asyncio\runners.py", line 204, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "C:\Program Files\Python314\Lib\asyncio\runners.py", line 127, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "C:\Program Files\Python314\Lib\asyncio\base_events.py", line 719, in run_until_complete      
    return future.result()
           ~~~~~~~~~~~~~^^
  File "D:\PHYTON\PROJECTS\CURSOR\pem08-master\venv\Lib\site-packages\uvicorn\server.py", line 71, in serve
    await self._serve(sockets)
  File "D:\PHYTON\PROJECTS\CURSOR\pem08-master\venv\Lib\site-packages\uvicorn\server.py", line 78, in _serve
    config.load()
    ~~~~~~~~~~~^^
  File "D:\PHYTON\PROJECTS\CURSOR\pem08-master\venv\Lib\site-packages\uvicorn\config.py", line 439, in load
    self.loaded_app = import_from_string(self.app)
                      ~~~~~~~~~~~~~~~~~~^^^^^^^^^^
  File "D:\PHYTON\PROJECTS\CURSOR\pem08-master\venv\Lib\site-packages\uvicorn\importer.py", line 19, in import_from_string
    module = importlib.import_module(module_str)
  File "C:\Program Files\Python314\Lib\importlib\__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1398, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1371, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1342, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 938, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 762, in exec_module
  File "<frozen importlib._bootstrap>", line 491, in _call_with_frames_removed
  File "d:\PHYTON\PROJECTS\CURSOR\pem08-master\backend\main.py", line 26, in <module>
    from backend.services.gemini_service import gemini_service
  File "d:\PHYTON\PROJECTS\CURSOR\pem08-master\backend\services\__init__.py", line 1, in <module>    
    from .gemini_service import GeminiService
  File "d:\PHYTON\PROJECTS\CURSOR\pem08-master\backend\services\gemini_service.py", line 129
    """Анализ изображения (баннер, сайт, упаковка)"""
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
IndentationError: expected an indented block after function definition on line 128