import json
import sys
import os
import urllib
import sublime
import sublime_plugin

class Pref:

    keys = [
        "show_debug",
        "jenkins_url",
    ]

    def load(self):
        self.settings = sublime.load_settings('jenkins-dashboard.sublime-settings')

        if sublime.active_window() is not None:
            project_settings = sublime.active_window().active_view().settings()
            if project_settings.has("jenkins-dashboard"):
                project_settings.clear_on_change('jenkins-dashboard')
                self.project_settings = project_settings.get('jenkins-dashboard')
                project_settings.add_on_change('jenkins-dashboard', pref.load)
            else:
                self.project_settings = {}
        else:
            self.project_settings = {}

        for key in self.keys:
            self.settings.clear_on_change(key)
            setattr(self, key, self.get_setting(key))
            self.settings.add_on_change(key, pref.load)

    def get_setting(self, key):
        if key in self.project_settings:
            return self.project_settings.get(key)
        else:
            return self.settings.get(key)

pref = Pref()

def plugin_loaded():
    pref.load()

def debug_message(msg):
    if pref.show_debug == True:
        print("[jenkins-dashboard] " + str(msg))


class Jenkins():
    """Jenkins Controller class"""
    def get_dashboard(self):
        build_report = []
        try:
            jenkins_url = pref.jenkins_url + "/api/json"
            debug_message("GET: " + jenkins_url)

            req = urllib.request.Request(jenkins_url)
            response = urllib.request.urlopen(req)

            jenkins_dashboard = response.read().decode('utf-8')
            debug_message(jenkins_dashboard)
        except urllib.error.URLError as e:
            debug_message("HTTP Error: " + str(e.code))
            return build_report

        try:
            dashboard_json = json.loads(jenkins_dashboard)
        except:
            debug_message("Unable to parse the jenkins json response")
            return build_report

        for job in dashboard_json['jobs']:
            if job['color'].find('blue') >= 0:
                build_report.append([job['name'], 'SUCCESS'])
            elif job['color'].find('red') >= 0:
                build_report.append([job['name'], 'FAILURE'])
            else:
                build_report.append([job['name'], 'UNSTABLE'])

        return build_report

    def build_job(self, jobName):
        try:
            jenkins_url = pref.jenkins_url + "/job/" + jobName + "/build"
            debug_message("POST: " + jenkins_url)

            req = urllib.request.Request(jenkins_url)
            data = urllib.parse.urlencode({'token': 1}) # Config needed here
            data = data.encode('utf-8')
            response = urllib.request.urlopen(req, data)

            return "HTTP Status Code: " + str(response.status)
        except urllib.error.URLError as e:
            return "HTTP Status Code: " + str(e.code) + "\nHTTP Status Reason: " + e.reason

    def get_job_report(self, jobName):
        try:
            jenkins_url = pref.jenkins_url + "/job/" + jobName + "/api/json"
            debug_message("GET: " + jenkins_url)

            req = urllib.request.Request(jenkins_url)
            response = urllib.request.urlopen(req)
            job_json = json.loads(response.read().decode('utf-8'))

            return json.dumps(job_json, indent=4, separators=(',', ': '))
        except urllib.error.URLError as e:
            return str(e.reason)


class BaseJenkinsDashboardCommand(sublime_plugin.TextCommand):
    """Base command class for Jenkins Dashboard"""
    description = ''

    def run(self, args):
        debug_message('Not implemented')

    def show_quick_panel(self, data):
        self.view.window().show_quick_panel(data, self.on_quick_panel_done)

    def on_quick_panel_done(self, picked):
        debug_message('Not implemented')
        return

    def render_jenkins_information(self, output):
        output_view = sublime.active_window().get_output_panel("jenkins-dashboard")
        output_view.set_read_only(False)
        output_view.run_command('output_helper', {'text': output})

        output_view.sel().clear()
        output_view.sel().add(sublime.Region(0))
        output_view.set_read_only(True)
        sublime.active_window().run_command("show_panel", {"panel": "output.jenkins-dashboard"})


class ShowJenkinsDashboardCommand(BaseJenkinsDashboardCommand):
    """Show the Jenkins Dashboard"""
    description = 'Show Jenkins Dashboard ...'
    build_report = []

    def is_enabled(self):
        if pref.jenkins_url != "":
            return True
        else:
            return False

    def run(self, args):
        cmd = Jenkins()
        self.build_report = cmd.get_dashboard()
        self.show_quick_panel(self.build_report)

    def on_quick_panel_done(self, picked):
        if picked == -1:
            return

        job = self.build_report[picked][0]
        cmd = Jenkins()
        job_report = cmd.get_job_report(job)
        self.render_jenkins_information(job_report)
        return


class BuildJenkinsJobCommand(BaseJenkinsDashboardCommand):
    """Show Jenkins Jobs and then build the one selected"""
    description = 'Build Jenkins Job ...'

    def is_enabled(self):
        if pref.jenkins_url != "":
            return True
        else:
            return False

    def run(self, args):
        cmd = Jenkins()
        self.build_report = cmd.get_dashboard()
        self.show_quick_panel(self.build_report)

    def on_quick_panel_done(self, picked):
        cmd = Jenkins()
        http_response_string = cmd.build_job(self.build_report[picked][0])
        self.render_jenkins_information(http_response_string)
        return