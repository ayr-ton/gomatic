#!/usr/bin/env python

from urllib2 import urlopen
import time
import os
import unittest

from gomatic import *


def start_go_server(gocd_version):
    with open('Dockerfile', 'w') as f:
        f.write(open("Dockerfile.tmpl").read().replace('GO-VERSION-REPLACE-ME', gocd_version))

    os.system("./build-and-run-go-server-in-docker %s" % gocd_version)

    def wait_for_go_server_to_start():
        for attempt in range(120):
            try:
                urlopen("http://localhost:8153").read()
                return
            except:
                time.sleep(1)
                print "Waiting for Docker-based Go server to start..."

    wait_for_go_server_to_start()


class populated_go_server:
    def __init__(self, gocd_version):
        self.gocd_version = gocd_version

    def __enter__(self):
        start_go_server(self.gocd_version)

        configurator = GoCdConfigurator(HostRestClient('localhost:8153'))
        pipeline = configurator \
            .ensure_pipeline_group("P.Group") \
            .ensure_replacement_of_pipeline("more-options") \
            .set_timer("0 15 22 * * ?") \
            .set_git_material(
            GitMaterial("git@bitbucket.org:springersbm/gomatic.git", material_name="some-material-name",
                        polling=False)) \
            .ensure_environment_variables(
            {'JAVA_HOME': '/opt/java/jdk-1.7'}) \
            .ensure_parameters({'environment': 'qa'})
        stage = pipeline.ensure_stage("earlyStage")
        job = stage.ensure_job("earlyWorm").ensure_artifacts(
            {BuildArtifact("scripts/*", "files"), BuildArtifact("target/universal/myapp*.zip", "artifacts"),
             TestArtifact("from", "to")}).set_runs_on_all_agents()
        job.add_task(ExecTask(['ls']))

        configurator.save_updated_config(save_config_locally=True)
        return GoCdConfigurator(HostRestClient('localhost:8153'))

    def __exit__(self, type, value, traceback):
        # stop go server
        pass


class IntegrationTest(unittest.TestCase):
    def test_all_versions(self):
        for gocd_version in ['13.4.0-18334']:  # , '14.4.0-1356']:
            with populated_go_server(gocd_version) as configurator:
                self.assertEquals(["P.Group"], [p.name() for p in configurator.pipeline_groups()])
                self.assertEquals(["more-options"], [p.name() for p in configurator.pipeline_groups()[0].pipelines()])


if __name__ == '__main__':
    unittest.main()
