import os
import sys
import platform
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext

class CMakeExtension(Extension):
    def __init__(self, name, sourcedir=''):
        Extension.__init__(self, name, sources=[])
        self.sourcedir = os.path.abspath(sourcedir)

class CMakeBuild(build_ext):
    def run(self):
        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext):
        extdir = os.path.abspath(os.path.dirname(self.get_ext_fullpath(ext.name)))
        cmake_args = [
            f'-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={extdir}',
            f'-DPYTHON_EXECUTABLE={sys.executable}'
        ]

        cfg = 'Debug' if self.debug else 'Release'
        build_args = ['--config', cfg]

        if platform.system() == "Windows":
            # Try to setup MinGW (download if needed)
            import shutil
            mingw_make = shutil.which('mingw32-make') or shutil.which('make')
            mingw_gcc = shutil.which('gcc')

            if not (mingw_make and mingw_gcc):
                # Try to download portable MinGW
                print("MinGW not found in PATH, attempting to download portable MinGW...")
                try:
                    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'build-scripts'))
                    from setup_cross_compile import setup_mingw_env
                    mingw_dir = setup_mingw_env()
                    mingw_bin = os.path.join(mingw_dir, 'bin')
                    mingw_gcc = os.path.join(mingw_bin, 'gcc.exe')
                    mingw_make = os.path.join(mingw_bin, 'mingw32-make.exe')
                    if not os.path.exists(mingw_make):
                        mingw_make = os.path.join(mingw_bin, 'make.exe')
                    print(f"Downloaded and setup MinGW at: {mingw_dir}")
                except Exception as e:
                    print(f"Failed to download MinGW: {e}")
                    mingw_gcc = None
                    mingw_make = None

            if mingw_make and mingw_gcc:
                # Use MinGW (compatible with ODAS build)
                print(f"Using MinGW: {mingw_gcc}")
                cmake_args += [
                    '-G', 'MinGW Makefiles',
                    f'-DCMAKE_C_COMPILER={mingw_gcc}',
                    f'-DCMAKE_CXX_COMPILER={mingw_gcc.replace("gcc", "g++")}',
                    f'-DCMAKE_MAKE_PROGRAM={mingw_make}',
                    f'-DCMAKE_BUILD_TYPE={cfg}'
                ]
                build_args = ['--', '-j4']
            else:
                # Fall back to MSVC but warn
                print("WARNING: MinGW not found and download failed, using MSVC (may have compatibility issues)")
                print("Install MinGW-w64 manually or ensure internet connection for automatic download")
                cmake_args += [f'-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_{cfg.upper()}={extdir}']
                if sys.maxsize > 2**32:
                    cmake_args += ['-A', 'x64']
                build_args += ['--', '/m']
        else:
            cmake_args += [f'-DCMAKE_BUILD_TYPE={cfg}']
            build_args += ['--', '-j4']

        env = os.environ.copy()
        env['CXXFLAGS'] = f"{env.get('CXXFLAGS', '')} -DVERSION_INFO=\\'{self.distribution.get_version()}\\'"

        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)

        import subprocess
        subprocess.check_call(['cmake', ext.sourcedir] + cmake_args, cwd=self.build_temp, env=env)
        subprocess.check_call(['cmake', '--build', '.'] + build_args, cwd=self.build_temp)

setup(
    name='odas-py',
    version='1.0.0',
    author='ODAS Python Bindings',
    description='Python bindings for ODAS (Open embeddeD Audition System)',
    long_description='Native Python bindings for ODAS real-time audio processing library',
    ext_modules=[CMakeExtension('odas_py._odas_core')],
    cmdclass={'build_ext': CMakeBuild},
    packages=['odas_py'],
    install_requires=['numpy>=1.19.0'],
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    zip_safe=False,
)