# Credits to AAlap Shah(https://github.com/fishfin) for his work on IBM DB integration with CF php-buildpack.


import logging
import os
import StringIO
from urlparse import urlparse
from build_pack_utils import stream_output
from build_pack_utils import utils
from extension_helpers import ExtensionHelper

PKGDOWNLOADS =  {
    #CLI_DRIVER
    'IBMDBCLIDRIVER1_DLFILE': 'linuxx64_odbc_cli.tar.gz',
    'IBMDBCLIDRIVER1_DLURL': 'https://public.dhe.ibm.com/ibmdl/export/pub/software/data/db2/drivers/odbc_cli/{IBMDBCLIDRIVER1_DLFILE}',

    #IBM_DB Packages
    'IBM_DB2_VERSION': '2.0.8',
    'IBM_DB2_DLFILE': 'ibm_db2-{IBM_DB2_VERSION}.so',
    'IBM_DB2_DLURL': 'https://github.com/jchallenger/php-buildpack/raw/master/extensions/ibmdb/bin/{IBM_DB2_DLFILE}',
}

class IBMDBInstaller(ExtensionHelper):

    def __init__(self, ctx):
        self._log = logging.getLogger(os.path.basename(os.path.dirname(__file__)))

        ExtensionHelper.__init__(self, ctx)
        self._compilationEnv = os.environ
        if 'IBM_DB_HOME' not in self._compilationEnv:
            self._compilationEnv['IBM_DB_HOME'] = ''
        if 'LD_LIBRARY_PATH' not in self._compilationEnv:
            self._compilationEnv['LD_LIBRARY_PATH'] = ''
        if 'PATH' not in self._compilationEnv:
            self._compilationEnv['PATH'] = ''

        self._ibmdbClidriverBaseDir = 'ibmdb_clidriver'
        self._phpBuildRootDpath = os.path.join(self._ctx['BUILD_DIR'], 'php')
        self._phpBuildIniFpath = os.path.join(self._phpBuildRootDpath, 'etc', 'php.ini')

    def _defaults(self):
        pkgdownloads = PKGDOWNLOADS
        pkgdownloads['COMPILATION_DIR'] = os.path.join(self._ctx['BUILD_DIR'], '.build_ibmdb_extension')
        pkgdownloads['DOWNLOAD_DIR'] = os.path.join('{COMPILATION_DIR}', '.downloads')
        pkgdownloads['IBMDBCLIDRIVER_INSTALL_DIR'] = os.path.join(self._ctx['BUILD_DIR'], 'ibmdb_clidriver')
        pkgdownloads['PHPSOURCE_INSTALL_DIR'] = os.path.join('{COMPILATION_DIR}', 'php')
        pkgdownloads['IBM_DB2_DLDIR'] = os.path.join('{PHPSOURCE_INSTALL_DIR}', 'ext', 'ibm_db')
        return utils.FormattedDict(pkgdownloads)

    def _should_configure(self):
        return False

    def _should_compile(self):
        return True

    def _configure(self):
        self._log.info(__file__ + "->configure")
        pass

    def _compile(self, install):
        self._log.info(__file__ + "->compile")
        self._installer = install._installer

        self._phpExtnDir = self.findPhpExtnBaseDir()
        self._zendModuleApiNo = self._phpExtnDir[len(self._phpExtnDir)-8:]
        self._phpExtnDpath = os.path.join(self._phpBuildRootDpath, 'lib', 'php', 'extensions', self._phpExtnDir)

        self.install_clidriver()
        self.install_extensions()
        self.modifyPhpIni()
        self.cleanup()
        return 0

    def _service_environment(self):
        self._log.info(__file__ + "->service_environment")
        env = {
            #'IBM_DB_HOME': '$IBM_DB_HOME:$HOME/' + self._ibmdbClidriverBaseDir + '/lib',
            'LD_LIBRARY_PATH': '$LD_LIBRARY_PATH:$HOME/' + self._ibmdbClidriverBaseDir + '/lib',
            'PATH': '$HOME/' + self._ibmdbClidriverBaseDir + '/bin:$HOME/'
                    + self._ibmdbClidriverBaseDir + '/adm:$PATH',
        }
        return env

    def _logMsg(self, logMsg):
        self._log.info(logMsg)
        print("IBM_DB2: " + logMsg)

    def _install_direct(self, url, hsh, installDir, fileName=None, strip=False, extract=True):
        if not fileName:
            fileName = urlparse(url).path.split('/')[-1]
        fileToInstall = os.path.join(self._ctx['TMPDIR'], fileName)
        self._runCmd(os.environ, self._ctx['BUILD_DIR'], ['rm', '-rf', fileToInstall])
        self._installer._dwn.custom_extension_download(url, url, fileToInstall)

        if extract:
            self._logMsg('Installing ' + fileToInstall + ' to ' + installDir)
            return self._installer._unzipUtil.extract(fileToInstall, installDir, strip)
        else:
            self._logMsg('Copying ' + fileToInstall + ' to ' + installDir)
            shutil.copy(fileToInstall, installDir)
            return installDir

    def _runCmd(self, environ, currWorkDir, cmd, displayRunLog=False):
        stringioWriter = StringIO.StringIO()
        try:
            self._logMsg("Running command: " + ' '.join(cmd))
            stream_output(stringioWriter, ' '.join(cmd), env=environ, cwd=currWorkDir, shell=True)
            cmdOutput = stringioWriter.getvalue()
            if displayRunLog:
                self._logMsg(cmdOutput)
        except:
            cmdOutput = stringioWriter.getvalue()
            print('-----> Command failed')
            print(cmdOutput)
            raise
        return cmdOutput

    def findPhpExtnBaseDir(self):
        with open(self._phpBuildIniFpath, 'rt') as phpIni:
            for line in phpIni.readlines():
                if line.startswith('extension_dir'):
                    (key, extnDir) = line.strip().split(' = ')
                    extnBaseDir = os.path.basename(extnDir.strip('"'))
                    return extnBaseDir

    def modifyPhpIni(self):
        with open(self._phpBuildIniFpath, 'rt') as phpIni:
            lines = phpIni.readlines()
        extns = [line for line in lines if line.startswith('extension=')]
        if len(extns) > 0:
            pos = lines.index(extns[-1]) + 1
        else:
            pos = lines.index('#{PHP_EXTENSIONS}\n') + 1

        lines.insert(pos, 'extension=ibm_db2.so\n')
        with open(self._phpBuildIniFpath, 'wt') as phpIni:
            for line in lines:
                phpIni.write(line)

    def install_clidriver(self):
        self._logMsg('-- Installing IBM DB CLI Drivers -----------------')
        for clidriverpart in ['ibmdbclidriver1']:
            if self._ctx[clidriverpart.upper() + '_DLFILE'] != '':
                self._install_direct(
                    self._ctx[clidriverpart.upper() + '_DLURL'],
                    None,
                    self._ctx['IBMDBCLIDRIVER_INSTALL_DIR'],
                    self._ctx[clidriverpart.upper() + '_DLFILE'],
                    True)

        self._compilationEnv['IBM_DB_HOME'] = self._ctx['IBMDBCLIDRIVER_INSTALL_DIR']
        self._logMsg('-- Installed IBM DB CLI Drivers ------------------')


    def install_extensions(self):
        self._logMsg('-- Downloading IBM DB Extension -----------------')
        ibmdbExtnDownloadDir = self._ctx['IBM_DB2_DLDIR']

        # download binary from our repo
        self._install_direct(
            self._ctx['IBM_DB2_DLURL'],
            None,
            ibmdbExtnDownloadDir,
            self._ctx['IBM_DB2_DLFILE'],
            False)

        # copy binary to extension folder
        self._runCmd(self._compilationEnv, self._ctx['BUILD_DIR'],
            ['cp', os.path.join(ibmdbExtnDownloadDir,  'ibm_db2.so'),
            self._phpExtnDpath])

        self._logMsg('-- Downloaded IBM DB Extension ------------------')

    def cleanup(self):
        self._logMsg('-- Some House-keeping ----------------------------')
        self._runCmd(os.environ, self._ctx['BUILD_DIR'], ['rm', '-rf', self._ctx['COMPILATION_DIR']])
        self._logMsg('-- House-keeping Done ----------------------------')

IBMDBInstaller.register(__name__)
