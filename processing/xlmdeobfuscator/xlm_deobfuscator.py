import re
import os
import json
from fame.common.utils import tempdir
from shutil import copyfile
from fame.core.module import ProcessingModule
from fame.common.exceptions import ModuleInitializationError

from ..docker_utils import HAVE_DOCKER, docker_client


def str_reverse(match):
    return match.group(1)[::-1]


class XLMDeobfuscator(ProcessingModule):
    name = "xlm_deobfuscator"
    description = "Extract and analyze Excel 4.0 macros."
    acts_on = ["excel", "xls", "xlsm"]

    def initialize(self):
        if not HAVE_DOCKER:
            raise ModuleInitializationError(self, "Missing dependency: docker")

        return True

    def run_xlmd(self, target):

        args = "-f {} -output-formula-format '[[INT-FORMULA]]' --export-json /data/output/results.json".format(
            target)

        # start the right docker
        return docker_client.containers.run(
            'fame/xlmdeobfuscator',
            args,
            volumes={self.outdir: {'bind': '/data', 'mode': 'rw'}},
            stderr=True,
            remove=True
        )

    def each(self, target):
        self.results = {
            'macros': u'',
            'analysis': {
                'IOC': [],
            }
        }

        self.outdir = tempdir()

        results_dir = os.path.join(self.outdir, 'output')

        if not os.path.isdir(results_dir):
            os.mkdir(results_dir)

        copyfile(target, os.path.join(self.outdir, os.path.basename(target)))

        regex_url = r"\w+:(\/\/)[^\s]+"
        reg = re.compile(regex_url)
        with open(os.path.join(results_dir, "results.json")) as results_json:
            data = json.load(results_json)
            for record in data['records']:
                self.results["macros"] = self.results["macros"] + "\n" + record['formula']
                for match in reg.finditer(record['formula']):
                    self.add_ioc(match.group(0))
                    self.results["IOC"].append(match.group(0))

        return len(self.results["macros"]) > 0
