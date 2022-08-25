#! /usr/bin/env python
#
#  setup.py : Distutils setup script
#
# ===================================================================
# The contents of this file are dedicated to the public domain.  To
# the extent that dedication to the public domain is not available,
# everyone is granted a worldwide, perpetual, royalty-free,
# non-exclusive license to exercise all rights associated with the
# contents of this file for any purpose whatsoever.
# No rights are reserved.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ===================================================================

from __future__ import print_function

try:
	from setuptools import Extension, Command, setup
	from setuptools.command.build_ext import build_ext
	from setuptools.command.build_py import build_py
except ImportError:
	from distutils.core import Extension, Command, setup
	from distutils.command.build_ext import build_ext
	from distutils.command.build_py import build_py

import os
import sys
import struct
import distutils
from distutils import ccompiler
from distutils.errors import CCompilerError


# region compiler_opt.py inlined

def test_compilation(program, extra_cc_options=None, extra_libraries=None,
					 msg=''):
	"""Test if a certain C program can be compiled."""

	# Create a temporary file with the C program
	if not os.path.exists("build"):
		os.makedirs("build")
	fname = os.path.join("build", "test1.c")
	f = open(fname, 'w')
	f.write(program)
	f.close()

	# Name for the temporary executable
	oname = os.path.join("build", "test1.out")

	debug = bool(os.environ.get('PYCRYPTODOME_DEBUG', None))
	# Mute the compiler and the linker
	if msg:
		print("Testing support for %s" % msg)
	if not (debug or os.name == 'nt'):
		old_stdout = os.dup(sys.stdout.fileno())
		old_stderr = os.dup(sys.stderr.fileno())
		dev_null = open(os.devnull, "w")
		os.dup2(dev_null.fileno(), sys.stdout.fileno())
		os.dup2(dev_null.fileno(), sys.stderr.fileno())

	objects = []
	try:
		compiler = ccompiler.new_compiler()
		distutils.sysconfig.customize_compiler(compiler)

		if compiler.compiler_type in ['msvc']:
			# Force creation of the manifest file (http://bugs.python.org/issue16296)
			# as needed by VS2010
			extra_linker_options = ["/MANIFEST"]
		else:
			extra_linker_options = []

		# In Unix, force the linker step to use CFLAGS and not CC alone (see GH#180)
		if compiler.compiler_type in ['unix']:
			compiler.set_executables(linker_exe=compiler.compiler)

		objects = compiler.compile([fname], extra_postargs=extra_cc_options)
		compiler.link_executable(objects, oname, libraries=extra_libraries,
								 extra_preargs=extra_linker_options)
		result = True
	except (CCompilerError, OSError):
		result = False
	for f in objects + [fname, oname]:
		try:
			os.remove(f)
		except OSError:
			pass

	# Restore stdout and stderr
	if not (debug or os.name == 'nt'):
		if old_stdout is not None:
			os.dup2(old_stdout, sys.stdout.fileno())
		if old_stderr is not None:
			os.dup2(old_stderr, sys.stderr.fileno())
		if dev_null is not None:
			dev_null.close()
	if msg:
		if result:
			x = ""
		else:
			x = " not"
		print("Target does%s support %s" % (x, msg))

	return result


def has_stdint_h():
	source = """
	#include <stdint.h>
	int main(void) {
		uint32_t u;
		u = 0;
		return u + 2;
	}
	"""
	return test_compilation(source, msg="stdint.h header")


def compiler_supports_uint128():
	source = """
	int main(void)
	{
		__uint128_t x;
		return 0;
	}
	"""
	return test_compilation(source, msg="128-bit integer")


def compiler_has_intrin_h():
	# Windows
	source = """
	#include <intrin.h>
	int main(void)
	{
		int a, b[4];
		__cpuid(b, a);
		return 0;
	}
	"""
	return test_compilation(source, msg="intrin.h header")


def compiler_has_cpuid_h():
	# UNIX
	source = """
	#include <cpuid.h>
	int main(void)
	{
		unsigned int eax, ebx, ecx, edx;
		__get_cpuid(1, &eax, &ebx, &ecx, &edx);
		return 0;
	}
	"""
	return test_compilation(source, msg="cpuid.h header")


def compiler_supports_aesni():
	source = """
	#include <wmmintrin.h>
	__m128i f(__m128i x, __m128i y) {
		return _mm_aesenc_si128(x, y);
	}
	int main(void) {
		return 0;
	}
	"""

	if test_compilation(source):
		return {'extra_cc_options': [], 'extra_macros': []}

	if test_compilation(source, extra_cc_options=['-maes'], msg='AESNI intrinsics'):
		return {'extra_cc_options': ['-maes'], 'extra_macros': []}

	return False


def compiler_has_posix_memalign():
	source = """
	#include <stdlib.h>
	int main(void) {
		void *new_mem;
		int res;
		res = posix_memalign((void**)&new_mem, 16, 101);
		return res == 0;
	}
	"""
	return test_compilation(source, msg="posix_memalign")


def compiler_has_memalign():
	source = """
	#include <malloc.h>
	int main(void) {
		void *p;
		p = memalign(16, 101);
		return p != (void*)0;
	}
	"""
	return test_compilation(source, msg="memalign")


def compiler_is_clang():
	source = """
	#if !defined(__clang__)
	#error Not clang
	#endif
	int main(void)
	{
		return 0;
	}
	"""
	return test_compilation(source, msg="clang")


def compiler_is_gcc():
	source = """
	#if defined(__clang__) || !defined(__GNUC__)
	#error Not GCC
	#endif
	int main(void)
	{
		return 0;
	}"""
	return test_compilation(source, msg="gcc")


def support_gcc_realign():
	source = """
	void __attribute__((force_align_arg_pointer)) a(void) {}
	int main(void) { return 0; }
	"""
	return test_compilation(source, msg="gcc")


def compiler_supports_sse2():
	source = """
	#include <intrin.h>
	int main(void)
	{
		__m128i r0;
		int mask;
		r0 = _mm_set1_epi32(0);
		mask = _mm_movemask_epi8(r0);
		return mask;
	}
	"""
	if test_compilation(source, msg="SSE2(intrin.h)"):
		return {'extra_cc_options': [], 'extra_macros': ['HAVE_INTRIN_H', 'USE_SSE2']}

	source = """
	#include <x86intrin.h>
	int main(void)
	{
		__m128i r0;
		int mask;
		r0 = _mm_set1_epi32(0);
		mask = _mm_movemask_epi8(r0);
		return mask;
	}
	"""
	if test_compilation(source, extra_cc_options=['-msse2'], msg="SSE2(x86intrin.h)"):
		return {'extra_cc_options': ['-msse2'], 'extra_macros': ['HAVE_X86INTRIN_H', 'USE_SSE2']}

	source = """
	#include <xmmintrin.h>
	#include <emmintrin.h>
	int main(void)
	{
		__m128i r0;
		int mask;
		r0 = _mm_set1_epi32(0);
		mask = _mm_movemask_epi8(r0);
		return mask;
	}
	"""
	if test_compilation(source, extra_cc_options=['-msse2'], msg="SSE2(emmintrin.h)"):
		return {'extra_cc_options': ['-msse2'], 'extra_macros': ['HAVE_EMMINTRIN_H', 'USE_SSE2']}

	return False


def remove_extension(extensions, name):
	idxs = [i for i, x in enumerate(extensions) if x.name == name]
	if len(idxs) != 1:
		raise ValueError("There is no or there are multiple extensions named '%s'" % name)
	del extensions[idxs[0]]


def set_compiler_options(package_root, extensions):
	"""Environment specific settings for extension modules.

	This function modifies how each module gets compiled, to
	match the capabilities of the platform.
	Also, it removes existing modules when not supported, such as:
	  - CLMUL
	"""

	extra_cc_options = []
	extra_macros = []

	clang = compiler_is_clang()
	gcc = compiler_is_gcc()

	if has_stdint_h():
		extra_macros.append(("HAVE_STDINT_H", None))

	# Endianess
	extra_macros.append(("PYCRYPTO_" + sys.byteorder.upper() + "_ENDIAN", None))

	# System
	system_bits = 8 * struct.calcsize("P")
	extra_macros.append(("SYS_BITS", str(system_bits)))

	# Disable any assembly in libtomcrypt files
	extra_macros.append(("LTC_NO_ASM", None))

	# Native 128-bit integer
	if compiler_supports_uint128():
		extra_macros.append(("HAVE_UINT128", None))

	# Auto-detecting CPU features
	cpuid_h_present = compiler_has_cpuid_h()
	if cpuid_h_present:
		extra_macros.append(("HAVE_CPUID_H", None))
	intrin_h_present = compiler_has_intrin_h()
	if intrin_h_present:
		extra_macros.append(("HAVE_INTRIN_H", None))

	# Platform-specific call for getting a block of aligned memory
	if compiler_has_posix_memalign():
		extra_macros.append(("HAVE_POSIX_MEMALIGN", None))
	elif compiler_has_memalign():
		extra_macros.append(("HAVE_MEMALIGN", None))

	# SSE2
	sse2_result = compiler_supports_sse2()
	if sse2_result:
		extra_cc_options.extend(sse2_result['extra_cc_options'])
		for macro in sse2_result['extra_macros']:
			extra_macros.append((macro, None))

	# Compiler specific settings
	if gcc:
		# On 32-bit x86 platforms, gcc assumes the stack to be aligned to 16
		# bytes, but the caller may actually only align it to 4 bytes, which
		# make functions crash if they use SSE2 intrinsics.
		# https://gcc.gnu.org/bugzilla/show_bug.cgi?id=40838
		if system_bits == 32 and support_gcc_realign():
			extra_macros.append(("GCC_REALIGN", None))

	# Module-specific options

	for x in extensions:
		x.extra_compile_args.extend(extra_cc_options)
		x.define_macros.extend(extra_macros)


# endregion


project_name = "ripemd"
package_root = "ripemd"

class PCTBuildExt(build_ext):
	# Avoid linking Python's dynamic library
	def get_libraries(self, ext):
		return []


class PCTBuildPy(build_py):
	def find_package_modules(self, package, package_dir, *args, **kwargs):
		modules = build_py.find_package_modules(self, package, package_dir,
												*args, **kwargs)

		# Exclude certain modules
		retval = []
		for item in modules:
			pkg, module = item[:2]
			retval.append(item)
		return retval


# Parameters for setup
packages =  [
	"ripemd",
]
package_data = {
}

ext_modules = [
	Extension("ripemd._ripemd160",
		include_dirs=['src/'],
		sources=["src/ripemd160.c"],
		depends=["src/common.h", "src/endianess.h", "src/errors.h"],
		py_limited_api=True)
]

# Add compiler specific options.
set_compiler_options(package_root, ext_modules)

# By doing this we need to change version information in a single file
with open(os.path.join("lib", package_root, "__init__.py")) as init_root:
	for line in init_root:
		if line.startswith("version_info"):
			version_tuple = eval(line.split("=")[1])

version_string = ".".join([str(x) for x in version_tuple])

with open('README.md', encoding='utf-8') as f:
	long_description = f.read()

setup(
	name=project_name,
	version=version_string,
	description="Ripemd library for Python",
	long_description=long_description,
	author="Symbol Contributors",
	author_email="contributors@symbol.dev",
	url="https://github.com/symbol/ripemd",
	platforms='Posix; MacOS X; Windows',
	zip_safe=False,
	python_requires='>=3.5',
	classifiers=[
		'Development Status :: 5 - Production/Stable',
		'License :: OSI Approved :: BSD License',
		'License :: OSI Approved :: Apache Software License',
		'License :: Public Domain',
		'Intended Audience :: Developers',
		'Operating System :: Unix',
		'Operating System :: Microsoft :: Windows',
		'Operating System :: MacOS :: MacOS X',
		'Topic :: Security :: Cryptography',
		'Programming Language :: Python :: 3',
		'Programming Language :: Python :: 3.5',
		'Programming Language :: Python :: 3.6',
		'Programming Language :: Python :: 3.7',
		'Programming Language :: Python :: 3.8',
		'Programming Language :: Python :: 3.9',
		'Programming Language :: Python :: 3.10',
	],
	license="BSD, Public Domain",
	packages=packages,
	package_dir={"": "lib"},
	package_data=package_data,
	cmdclass={
		'build_ext': PCTBuildExt,
		'build_py': PCTBuildPy
		},
	ext_modules=ext_modules,
)
