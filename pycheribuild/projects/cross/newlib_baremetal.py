#
# Copyright (c) 2017 Alex Richardson
# All rights reserved.
#
# This software was developed by SRI International and the University of
# Cambridge Computer Laboratory under DARPA/AFRL contract FA8750-10-C-0237
# ("CTSRD"), as part of the DARPA CRASH research programme.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
from .crosscompileproject import *
from ...utils import statusUpdate
from ...config.loader import ComputedDefaultValue


class BuildNewlibBaremetal(CrossCompileAutotoolsProject):
    repository = "git://sourceware.org/git/newlib-cygwin.git"
    projectName = "newlib-baremetal"
    requiresGNUMake = True
    add_host_target_build_config_options = False
    defaultOptimizationLevel = ["-O2"]
    _configure_supports_libdir = False
    _configure_supports_variables_on_cmdline = True
    crossInstallDir = CrossInstallDir.NONE
    defaultInstallDir = ComputedDefaultValue(function=lambda c, p: c.sdkSysrootDir / "baremetal", asString="$SDK/sysroot/baremetal")

    # defaultBuildDir = CrossCompileAutotoolsProject.defaultSourceDir  # we have to build in the source directory

    def __init__(self, config: CheriConfig):
        if self.crossCompileTarget == CrossCompileTarget.CHERI:
            statusUpdate("Cannot compile newlib in purecap mode, building mips instead")
            # self.crossCompileTarget = CrossCompileTarget.MIPS  # won't compile as a CHERI binary!
        self.crossCompileTarget = CrossCompileTarget.NATIVE  # HACK
        super().__init__(config)
        self.configureCommand = self.sourceDir / "configure"
        # self.COMMON_FLAGS = ['-integrated-as', '-G0', '-mabi=n64', '-mcpu=mips4']
        # self.COMMON_FLAGS = ['-integrated-as', '-mabi=n64', '-mcpu=mips4']
        self.COMMON_FLAGS = []
        self.triple = "mips64-qemu-elf"
        # FIXME: how can I force it to run a full configure step (this is needed because it runs the newlib configure
        # step during make all rather than during ./configure
        self.target_cflags = " -target " + self.targetTripleWithVersion + " -integrated-as -mabi=n64 -mcpu=mips4"
        self.add_configure_vars(
            AS_FOR_TARGET=str(self.sdkBinDir / "clang"), # + target_cflags,
            CC_FOR_TARGET=str(self.sdkBinDir / "clang"), # + target_cflags,
            CXX_FOR_TARGET=str(self.sdkBinDir / "clang++"), # + target_cflags,
            LD_FOR_TARGET=str(self.sdkBinDir / "ld.bfd"), LDFLAGS_FOR_TARGET="-fuse-ld=bfd",
            AR=self.sdkBinDir / "ar", STRIP=self.sdkBinDir / "strip",
            AR_FOR_TARGET=self.sdkBinDir / "ar", STRIP_FOR_TARGET=self.sdkBinDir / "strip",
            OBJCOPY=self.sdkBinDir / "objcopy", RANLIB=self.sdkBinDir / "ranlib",
            OBJCOPY_FOR_TARGET=self.sdkBinDir / "objcopy", RANLIB_FOR_TARGET=self.sdkBinDir / "ranlib",
            OBJDUMP_FOR_TARGET=self.sdkBinDir / "llvm-objdump",
            READELF=self.sdkBinDir / "readelf", NM=self.sdkBinDir / "nm",
            READELF_FOR_TARGET=self.sdkBinDir / "readelf", NM_FOR_TARGET=self.sdkBinDir / "nm",
            # Some build tools are needed:
            CC_FOR_BUILD=self.config.clangPath,
            CXX_FOR_BUILD=self.config.clangPlusPlusPath,
            CC=self.config.clangPath,
            CXX=self.config.clangPlusPlusPath,
            # long double is the same as double
            newlib_cv_ldbl_eq_dbl="yes",
            CFLAGS_FOR_TARGET=self.target_cflags,
            CCASFLAGS_FOR_TARGET=self.target_cflags,
            FLAGS_FOR_TARGET=self.target_cflags,
        )

    def install(self, **kwargs):
        super().install()

    def needsConfigure(self):
        return not (self.buildDir / "Makefile").exists()

    @property
    def targetTripleWithVersion(self):
        return "mips64-unknown-elf"

    def add_configure_vars(self, **kwargs):
        # newlib is annoying, we need to pass all these arguments to make as well because it won't run all
        # the configure steps...
        super().add_configure_vars(**kwargs)
        for k, v in kwargs.items():
            self.make_args.env_vars[k] = str(v)

    def configure(self):
        self.configureArgs.extend([
            "--enable-malloc-debugging",
            "--enable-newlib-long-time_t",
            "--enable-newlib-io-c99-formats",
            "--enable-newlib-io-long-long",
            "--disable-newlib-io-long-double"
            # "--disable-newlib-supplied-syscalls"
            "--disable-newlib-mb",
            "--disable-libstdcxx",
            "--disable-newlib-io-float",

            "--enable-newlib-global-atexit",
            # TODO: smaller lib? "--enable-target-optspace"

            # FIXME: these don't seem to work
            "--enable-serial-build-configure",
            "--enable-serial-target-configure",
            "--enable-serial-host-configure",
        ])

        # self.configureArgs.append("--host=" + self.triple)
        self.configureArgs.append("--target=" + self.triple)
        self.configureArgs.append("--disable-multilib")
        self.configureArgs.append("--with-newlib")
        super().configure()

