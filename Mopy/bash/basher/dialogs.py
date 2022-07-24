# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, either version 3
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <https://www.gnu.org/licenses/>.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from . import bEnableWizard
from .constants import installercons
from .. import bass, balt, bosh, bolt, bush, env, load_order
from ..balt import colors
from ..bolt import FName, top_level_dirs, text_wrap
from ..bosh import faces, ModInfo, InstallerProject
from ..fomod_schema import default_moduleconfig
from ..gui import BOTTOM, CancelButton, CENTER, CheckBox, GridLayout, \
    HLayout, Label, LayoutOptions, OkButton, RIGHT, Stretch, TextField, \
    VLayout, DialogWindow, ListBox, Picture, DropDown, CheckListBox, \
    HBoxedLayout, SelectAllButton, DeselectAllButton, VBoxedLayout, \
    TextAlignment, SearchBar, bell, EventResult, Spacer

class ImportFaceDialog(DialogWindow):
    """Dialog for importing faces."""
    _min_size = (550, 300)

    def __init__(self, parent, title, fileInfo, faces):
        #--Data
        self.fileInfo = fileInfo
        if faces and isinstance(next(iter(faces)), int):
            self.fdata = {f'{int_key:08X} {face.pcName}': face for
                          int_key, face in faces.items()}
        else:
            self.fdata = faces
        self.list_items = sorted(self.fdata, key=str.lower)
        #--GUI
        super(ImportFaceDialog, self).__init__(parent, title=title,
                                               sizes_dict=balt.sizes)
        #--List Box
        self.listBox = ListBox(self, choices=self.list_items,
                               onSelect=self.EvtListBox)
        self.listBox.set_min_size(175, 150)
        #--Name,Race,Gender Checkboxes
        fi_flgs = bosh.faces.PCFaces.pcf_flags(
            bass.settings.get(u'bash.faceImport.flags', 0x4))
        self.nameCheck = CheckBox(self, _(u'Name'), checked=fi_flgs.pcf_name)
        self.raceCheck = CheckBox(self, _(u'Race'), checked=fi_flgs.race)
        self.genderCheck = CheckBox(self, _(u'Gender'), checked=fi_flgs.gender)
        self.statsCheck = CheckBox(self, _(u'Stats'), checked=fi_flgs.stats)
        self.classCheck = CheckBox(self, _(u'Class'), checked=fi_flgs.iclass)
        #--Name,Race,Gender Text
        self.nameText = Label(self, '-----------------------------')
        self.raceText = Label(self, '')
        self.genderText = Label(self, '')
        self.statsText = Label(self, '')
        self.classText = Label(self, '')
        #--Other
        importButton = OkButton(self, btn_label=_(u'Import'))
        importButton.on_clicked.subscribe(self.DoImport)
        self.picture = Picture(self, 350, 210, scaling=2) ##: unused
        GridLayout(border=4, stretch_cols=[0, 1], stretch_rows=[0], items=[
            # Row 1
            ((self.listBox, LayoutOptions(row_span=2, expand=True)),
             (self.picture, LayoutOptions(col_span=2, expand=True))),
            # Row 2
            (None,  # note the row_span in the prev row
             GridLayout(h_spacing=4, v_spacing=2, stretch_cols=[1], items=[
                 (self.nameCheck, self.nameText),
                 (self.raceCheck, self.raceText),
                 (self.genderCheck, self.genderText),
                 (self.statsCheck, self.statsText),
                 (self.classCheck, self.classText)]),
             (VLayout(spacing=4, items=[importButton, CancelButton(self)]),
              LayoutOptions(h_align=RIGHT, v_align=BOTTOM)))
        ]).apply_to(self)

    def EvtListBox(self, lb_selection_dex, lb_selection_str):
        """Responds to listbox selection."""
        item = self.list_items[lb_selection_dex]
        face = self.fdata[item]
        self.nameText.label_text = face.pcName
        self.raceText.label_text = face.getRaceName()
        self.genderText.label_text = face.getGenderName()
        self.statsText.label_text = _(u'Health ') + str(face.health)
        itemImagePath = bass.dirs['mods'].join('Docs', 'Images', f'{item}.jpg')
        # TODO(ut): any way to get the picture ? see mod_links.Mod_Face_Import
        self.picture.set_bitmap(itemImagePath)
        self.listBox.lb_select_index(lb_selection_dex)

    def DoImport(self):
        """Imports selected face into save file."""
        selections = self.listBox.lb_get_selections()
        if not selections:
            bell()
            return
        itemDex = selections[0]
        item = self.list_items[itemDex]
        #--Do import
        pc_flags = bosh.faces.PCFaces.pcf_flags() # make a copy of PCFaces flags
        pc_flags.hair = pc_flags.eye = True
        pc_flags.pcf_name = self.nameCheck.is_checked
        pc_flags.race = self.raceCheck.is_checked
        pc_flags.gender = self.genderCheck.is_checked
        pc_flags.stats = self.statsCheck.is_checked
        pc_flags.iclass = self.classCheck.is_checked
        #deprint(flags.getTrueAttrs())
        bass.settings[u'bash.faceImport.flags'] = int(pc_flags)
        bosh.faces.PCFaces.save_setFace(self.fileInfo, self.fdata[item],
                                        pc_flags)
        balt.showOk(self, _(u'Face imported.'), self.fileInfo.fn_key)
        self.accept_modal()

#------------------------------------------------------------------------------
class CreateNewProject(DialogWindow):
    title = _(u'New Project')
    def __init__(self, parent):
        self._parent = parent
        super(CreateNewProject, self).__init__(parent)
        # Build a list of existing directories. The text control will use this
        # to change background color when name collisions occur.
        self.existingProjects = {x for x in  ##: use idata?
                                 top_level_dirs(bass.dirs[u'installers'])}
        #--Attributes
        self._project_name = TextField(self, _('Project Name Goes Here'))
        self._project_name.on_text_changed.subscribe(
            self.OnCheckProjectsColorTextCtrl)
        self._check_esp = CheckBox(self, _('Blank.esp'), checked=True,
            chkbx_tooltip=_('Include a blank plugin file with only the '
                            '%(game_master)s as a master in the project.') % {
                'game_master': bush.game.master_file})
        self._check_esp_masterless = CheckBox(self, _('Blank Masterless.esp'),
            chkbx_tooltip=_('Include a blank plugin file without any masters '
                            'in the project.'))
        self._check_wizard = CheckBox(self, _('Blank wizard.txt'),
            chkbx_tooltip=_('Include a blank BAIN wizard in the project.'))
        self._check_fomod = CheckBox(self, _('Blank ModuleConfig.xml'),
            chkbx_tooltip=_('Include a blank FOMOD config in the project.'))
        self._check_wizard_images = CheckBox(self,
            _('Wizard Images Directory'), chkbx_tooltip=_(
                'Include an empty Wizard Images directory in the project.'))
        self._check_docs = CheckBox(self, _('Docs Directory'),
            chkbx_tooltip=_('Include an empty Docs directory in the project.'))
        for checkbox in (self._check_esp, self._check_esp_masterless,
                         self._check_wizard):
            checkbox.on_checked.subscribe(self.OnCheckBoxChange)
        if not bEnableWizard:
            # pywin32 not installed
            self._check_wizard.enabled = False
            self._check_wizard_images.enabled = False
        # Panel Layout
        self.ok_button = OkButton(self)
        self.ok_button.on_clicked.subscribe(self.OnClose)
        VLayout(border=5, spacing=5, items=[
            (VBoxedLayout(self,
                title=_(u'What do you want to name the new project?'),
                item_expand=True, item_weight=1, items=[
                    self._project_name,
                ]), LayoutOptions(expand=True)),
            VBoxedLayout(self, spacing=5,
                title=_('What do you want to add to the new project?'),
                items=[
                    self._check_esp, self._check_esp_masterless,
                    self._check_wizard, self._check_fomod,
                    self._check_wizard_images, self._check_docs,
                ]),
            Stretch(),
            (HLayout(spacing=5, items=[self.ok_button, CancelButton(self)]),
             LayoutOptions(h_align=CENTER))
        ]).apply_to(self, fit=True)
        # Dialog Icon Handlers
        self.set_icon(installercons.get_icon('off.red.dir'))
        self.OnCheckBoxChange()
        self.OnCheckProjectsColorTextCtrl(self._project_name.text_content)

    def OnCheckProjectsColorTextCtrl(self, new_text):
        projectName = FName(new_text)
        if existing := projectName in self.existingProjects:
            self._project_name.set_background_color(colors['default.warn'])
            self._project_name.tooltip = _('There is already a project with '
                                           'that name!')
        else:
            self._project_name.reset_background_color()
            self._project_name.tooltip = None
        self.ok_button.enabled = not existing

    def OnCheckBoxChange(self, is_checked=None):
        """Change the DialogWindow icon to represent what the project status
        will be when created. """
        if self._check_esp.is_checked or self._check_esp_masterless.is_checked:
            img_key = f'off.red.dir' \
                      f'{self._check_wizard.is_checked and ".wiz" or ""}'
        else:
            img_key = 'off.grey.dir'
        self.set_icon(installercons.get_icon(img_key))

    def OnClose(self):
        """ Create the New Project and add user specified extras. """
        projectName = self._project_name.text_content.strip()
        # Destination project directory in installers dir
        projectDir = bass.dirs[u'installers'].join(projectName)
        if projectDir.exists():
            balt.showError(self, _(
                u'There is already a project with that name!') + u'\n' + _(
                u'Pick a different name for the project and try again.'))
            return
        # Create project in temp directory, so we can move it via
        # Shell commands (UAC workaround) ##: TODO(ut) needed?
        tmpDir = bolt.Path.tempDir()
        tempProject = tmpDir.join(projectName)
        blank_esp_name = f'Blank, {bush.game.displayName}.esp'
        if self._check_esp.is_checked:
            bosh.modInfos.create_new_mod(blank_esp_name, dir_path=tempProject)
        blank_ml_name = f'Blank, {bush.game.displayName} (masterless).esp'
        if self._check_esp_masterless.is_checked:
            bosh.modInfos.create_new_mod(blank_ml_name, dir_path=tempProject,
                                         wanted_masters=[])
        if self._check_wizard.is_checked:
            # Create (mostly) empty wizard.txt
            wizardPath = tempProject.join(u'wizard.txt')
            with wizardPath.open(u'w', encoding=u'utf-8') as out:
                out.write(f'; {projectName} BAIN Wizard Installation Script\n')
                out.write(f'; Created by Wrye Bash v{bass.AppVersion}\n')
                # Put an example SelectPlugin statement in if possible
                if self._check_esp.is_checked:
                    out.write(f'SelectPlugin "{blank_esp_name}"\n')
                if self._check_esp_masterless.is_checked:
                    out.write(f'SelectPlugin "{blank_ml_name}"\n')
        if self._check_fomod.is_checked:
            # Create (mostly) empty ModuleConfig.xml
            fomod_path = tempProject.join('fomod')
            fomod_path.makedirs()
            module_config_path = fomod_path.join('ModuleConfig.xml')
            with module_config_path.open('w', encoding='utf-8') as out:
                out.write(default_moduleconfig % {
                    'fomod_proj': projectName, 'wb_ver': bass.AppVersion,
                })
        if self._check_wizard_images.is_checked:
            # Create 'Wizard Images' directory
            tempProject.join(u'Wizard Images').makedirs()
        if self._check_docs.is_checked:
            #Create the 'Docs' Directory
            tempProject.join(u'Docs').makedirs()
        # HACK: shellMove fails unless it has at least one file - means
        # creating an empty project fails silently unless we make one
        has_files = bool([*tempProject.ilist()])
        if not has_files: tempProject.join(u'temp_hack').makedirs()
        # Move into the target location
        # TODO(inf) de-wx! Investigate further
        env.shellMove(tempProject, projectDir, parent=self._native_widget)
        tmpDir.rmtree(tmpDir.s)
        if not has_files:
            projectDir.join(u'temp_hack').rmtree(safety=u'temp_hack')
        fn_result_proj = FName(projectDir.stail)
        new_installer_order = 0
        sel_installers = self._parent.GetSelectedInfos()
        if sel_installers:
            new_installer_order = sel_installers[-1].order + 1
        ##: This is mostly copy-pasted from InstallerArchive_Unpack
        with balt.Progress(_('Creating Project...')) as prog:
            InstallerProject.refresh_installer(
                fn_result_proj, self._parent.data_store, progress=prog,
                install_order=new_installer_order, do_refresh=False)
        self._parent.data_store.irefresh(what='NS')
        self._parent.RefreshUI(detail_item=fn_result_proj)
        self._parent.SelectItemsNoCallback([fn_result_proj])

#------------------------------------------------------------------------------
class CreateNewPlugin(DialogWindow):
    """Dialog for creating a new plugin, allowing the user to select extension,
    name and flags."""
    title = _(u'New Plugin')
    _def_size = (400, 500)

    def __init__(self, parent):
        super(CreateNewPlugin, self).__init__(parent, sizes_dict=balt.sizes)
        self._parent_window = parent
        self._plugin_ext = DropDown(self, value='.esp',
            choices=sorted(bush.game.espm_extensions), auto_tooltip=False)
        self._plugin_ext.tooltip = _(u'Select which extension the plugin will '
                                     u'have.')
        self._plugin_ext.on_combo_select.subscribe(self._handle_plugin_ext)
        self._plugin_name = TextField(self, _(u'New Plugin'),
            alignment=TextAlignment.RIGHT)
        self._esm_flag = CheckBox(self, _(u'ESM Flag'),
            chkbx_tooltip=_(u'Whether or not the the resulting plugin will be '
                            u'a master, i.e. have the ESM flag.'))
        # Completely hide the ESL checkbox for non-ESL games, but check it by
        # default for ESL games, since one of the most common use cases for
        # this command on those games is to create BSA-loading dummies.
        self._esl_flag = CheckBox(self, _(u'ESL Flag'),
            chkbx_tooltip=_(u'Whether or not the resulting plugin will be '
                            u'light, i.e have the ESL flag.'),
            checked=bush.game.has_esl)
        self._esl_flag.visible = bush.game.has_esl
        self._master_search = SearchBar(self, hint=_('Search Masters'))
        self._master_search.on_text_changed.subscribe(self._handle_search)
        self._masters_box = CheckListBox(self)
        # Initially populate the masters list, checking only the game master
        self._masters_dict = {m: m == bush.game.master_file for m in
                              load_order.cached_lo_tuple()}
        self._masters_box.set_all_items(self._masters_dict)
        # Only once that's done do we subscribe - avoid all the initial events
        self._masters_box.on_box_checked.subscribe(self._handle_master_checked)
        select_all_btn = SelectAllButton(self,
            btn_tooltip=_(u'Select all plugins that are visible with the '
                          u'current search term.'))
        select_all_btn.on_clicked.subscribe(
            lambda: self._handle_mass_select(mark_active=True))
        deselect_all_btn = DeselectAllButton(self,
            btn_tooltip=_(u'Deselect all plugins that are visible with the '
                          u'current search term.'))
        deselect_all_btn.on_clicked.subscribe(
            lambda: self._handle_mass_select(mark_active=False))
        self._ok_btn = OkButton(self)
        self._ok_btn.on_clicked.subscribe(self._handle_ok)
        self._too_many_masters = Label(self, u'')
        self._too_many_masters.set_foreground_color(colors[u'default.warn'])
        self._too_many_masters.visible = False
        VLayout(border=6, spacing=6, item_expand=True, items=[
            HLayout(spacing=4, items=[
                (self._plugin_name, LayoutOptions(weight=1)),
                self._plugin_ext,
            ]),
            VBoxedLayout(self, title=_(u'Flags'), spacing=4, items=[
                self._esm_flag, self._esl_flag,
            ]),
            (HBoxedLayout(self, title=_(u'Masters'), spacing=4,
                item_expand=True, items=[
                    (VLayout(item_expand=True, spacing=4, items=[
                        self._master_search,
                        (self._masters_box, LayoutOptions(weight=1)),
                    ]), LayoutOptions(weight=1)),
                    VLayout(spacing=4, items=[
                        select_all_btn, deselect_all_btn,
                    ]),
            ]), LayoutOptions(weight=1)),
            VLayout(item_expand=True, items=[
                self._too_many_masters,
                HLayout(spacing=5, item_expand=True, items=[
                    Stretch(), self._ok_btn, CancelButton(self)
                ]),
            ]),
        ]).apply_to(self)

    @property
    def _chosen_masters(self):
        """Returns a generator yielding all checked masters."""
        return (k for k, v in self._masters_dict.items() if v)

    def _check_master_limit(self):
        """Checks if the current selection of masters exceeds the game's master
        limit and, if so, disables the OK button and shows a warning
        message."""
        count_checked = len(list(self._chosen_masters))
        count_limit = bush.game.Esp.master_limit
        limit_exceeded = count_checked > count_limit
        self._ok_btn.enabled = not limit_exceeded
        self._too_many_masters.visible = limit_exceeded
        if limit_exceeded:
            # Only update if limit exceeded to avoid the wx update/redraw cost
            self._too_many_masters.label_text = _(
                'Too many masters: %u checked, but only %u are allowed by the '
                'game.') % (count_checked, count_limit)
        self.update_layout()

    def _handle_plugin_ext(self, new_p_ext):
        """Internal callback to handle a change in extension."""
        # Enable the flags by default, but don't mess with their checked state
        p_is_esl = new_p_ext == '.esl'
        p_is_master = p_is_esl or new_p_ext == '.esm'
        # For .esm and .esl files, force-check the ESM flag
        if p_is_master:
            self._esm_flag.is_checked = True
        self._esm_flag.enabled = not p_is_master
        # For .esl files, force-check the ESL flag
        if p_is_esl:
            self._esl_flag.is_checked = True
        self._esl_flag.enabled = not p_is_esl

    def _handle_mass_select(self, mark_active):
        """Internal callback to handle the Select/Deselect All buttons."""
        self._masters_box.set_all_checkmarks(checked=mark_active)
        for m in self._masters_box.lb_get_str_items():
            # Update only visible items!
            self._masters_dict[FName(m)] = mark_active
        self._check_master_limit()

    def _handle_master_checked(self, master_index):
        """Internal callback to update the dict we use to track state,
        independent of the contents of the masters box."""
        mast_name = self._masters_box.lb_get_str_item_at_index(master_index)
        mast_checked = self._masters_box.lb_is_checked_at_index(master_index)
        self._masters_dict[FName(mast_name)] = mast_checked
        self._check_master_limit()

    def _handle_search(self, search_str):
        """Internal callback used to repopulate the masters box whenever the
        text in the search bar changes."""
        lower_search_str = search_str.strip().lower()
        # Case-insensitively filter based on the keys, then update the box
        new_m_items = {k: v for k, v in self._masters_dict.items() if
                       lower_search_str in k.lower()}
        self._masters_box.set_all_items(new_m_items)

    def _handle_ok(self):
        """Internal callback to handle the OK button."""
        pw = self._parent_window
        pl_name = self._plugin_name.text_content + self._plugin_ext.get_value()
        newName, root = ModInfo.validate_filename_str(pl_name)
        if root is None:
            balt.showError(self, newName)
            self._plugin_name.set_focus()
            self._plugin_name.select_all_text()
            return EventResult.FINISH # leave the dialog open
        chosen_name = ModInfo.unique_name(newName)
        windowSelected = pw.GetSelected()
        pw.data_store.create_new_mod(chosen_name, windowSelected,
            esm_flag=self._esm_flag.is_checked,
            esl_flag=self._esl_flag.is_checked,
            wanted_masters=[*map(FName, self._chosen_masters)])
        if windowSelected:  # assign it the group of the first selected mod
            mod_group = pw.data_store.table.getColumn(u'group')
            mod_group[chosen_name] = mod_group.get(windowSelected[0], u'')
        pw.ClearSelected(clear_details=True)
        pw.RefreshUI(redraw=[chosen_name], refreshSaves=False)

#------------------------------------------------------------------------------
class ExportScriptsDialog(DialogWindow):
    """Dialog for exporting script sources from a plugin."""
    title = _('Export Scripts Options')

    def __init__(self, parent):
        super().__init__(parent)
        self._skip_prefix = TextField(self)
        self._skip_prefix.text_content = bass.settings[
            'bash.mods.export.skip']
        self._remove_prefix = TextField(self)
        self._remove_prefix.text_content = bass.settings[
            'bash.mods.export.deprefix']
        self._skip_comments = CheckBox(self, _('Filter Out Comments'),
          chkbx_tooltip=_('Whether or to include comments in the exported '
                          'scripts.'))
        self._skip_comments.is_checked = bass.settings[
            'bash.mods.export.skipcomments']
        msg = _('Removes a prefix from the exported file names, e.g. enter '
                'cob to save script cobDenockInit as DenockInit.txt rather '
                'than as cobDenockInit.txt (case-insensitive, leave blank to '
                'not remove any prefix):')
        ok_button = OkButton(self)
        ok_button.on_clicked.subscribe(self._on_ok)
        VLayout(border=6, spacing=4, items=[
            Label(self, _('Skip prefix (leave blank to not skip any), '
                          'case-insensitive):')),
            (self._skip_prefix, LayoutOptions(expand=True)),
            Spacer(10),
            Label(self, text_wrap(msg, 80)),
            (self._remove_prefix, LayoutOptions(expand=True)),
            Spacer(10),
            self._skip_comments, Stretch(),
            (HLayout(spacing=4, items=[
                ok_button,
                CancelButton(self),
            ]), LayoutOptions(h_align=RIGHT)),
        ]).apply_to(self, fit=True)

    def _on_ok(self):
        pfx_skip = self._skip_prefix.text_content.strip()
        bass.settings['bash.mods.export.skip'] = pfx_skip
        pfx_remove = self._remove_prefix.text_content.strip()
        bass.settings['bash.mods.export.deprefix'] = pfx_remove
        cmt_skip = self._skip_comments.is_checked
        bass.settings['bash.mods.export.skipcomments'] = cmt_skip
