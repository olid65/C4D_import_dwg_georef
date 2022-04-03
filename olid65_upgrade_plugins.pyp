import c4d
import os
from urllib.request import urlopen
from io import BytesIO
from zipfile import ZipFile
from pprint import pprint
import shutil

# Be sure to use a unique ID obtained from www.plugincafe.com
PLUGIN_ID = 1059297

class UpgradePluginsOlid65(c4d.plugins.CommandData):
        
    def Execute(self, doc):       
        path_dst = os.path.join(c4d.storage.GeGetStartupWritePath(),'plugins')
        path_dst = '/Users/olivierdonze/Documents/TEMP/Test_import_plugins_olid65'

        urls = ['https://github.com/olid65/C4D_import_dwg_georef/archive/refs/heads/main.zip',
                'https://github.com/olid65/ESRI_extractor/archive/refs/heads/main.zip',
                'https://github.com/olid65/SITG_C4D/archive/refs/heads/master.zip',
                'https://github.com/olid65/swisstopo_extractor/archive/refs/heads/master.zip'
            ]
        
        rep = c4d.gui.QuestionDialog(f"Attention, l'opération va remplacer tous les plugins d'olid65 contenus dans {path_dst}.\n\nVoulez-vous vraiment continuer ?")
        if not rep: return

        for url in urls:
            with urlopen(url) as zipresp:
                with ZipFile(BytesIO(zipresp.read())) as zfile:
                    zfile.extractall(path_dst)

        with urlopen(url) as zipresp:
            with ZipFile(BytesIO(zipresp.read())) as zfile:
                zfile.extractall(path_dst)
        #suppression des -main ou -master
        lst_supp = ['-main','-master']

        for dir_name in os.listdir(path_dst):
            for txt in lst_supp:
                if dir_name[-len(txt):] == txt:
                    old_name = os.path.join(path_dst,dir_name)
                    new_name = os.path.join(path_dst,dir_name[:-len(txt)])
                    if os.path.isdir(new_name):
                        shutil.rmtree(new_name)
                    os.rename(old_name, new_name)

        rep = c4d.gui.QuestionDialog(f"Pour terminer l'installation Cinema4D doit redémarrer, voulez-vous le faire maintenant ?")
        if not rep: return

        c4d.RestartMe()

        return True

    


# main
if __name__ == "__main__":
    # Registers the plugin
    c4d.plugins.RegisterCommandPlugin(id=PLUGIN_ID,
                                      str="Mettre à jour les plugins d'olid65",
                                      info=0,
                                      help="Télécharge et installe les plugins C4D d'olid65 depuis Github",
                                      dat=UpgradePluginsOlid65(),
                                      icon=None)
