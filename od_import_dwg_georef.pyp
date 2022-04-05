import c4d
import os.path
from pprint import pprint

# Be sure to use a unique ID obtained from www.plugincafe.com
PLUGIN_ID = 1059197

TXT_NOT_DWG = "Ce n'est pas un document dwg !"
TXT_PB_OPEN_DWG = "Problème à l'ouverture du fichier dwg !"

DOC_NOT_IN_METERS_TXT = "Les unités du document ne sont pas en mètres, si vous continuez les unités seront modifiées.\nVoulez-vous continuer ?"

CONTAINER_ORIGIN =1026473

ALERT_SIZE_FN = 10 #taille pour alerter si un document est trop gros en Mo

#Emprise des coordonnées 
CH_XMIN, CH_YMIN, CH_XMAX, CH_YMAX = 1988000.00, 87000.00, 2906900.00, 1421600.00



def getAllLayers(lyr,res = {}):
    """fonction recursive qui renvoie un dico
       nom calque, liste de calques"""
    while lyr:
        res.setdefault(lyr.GetName(),[]).append(lyr)
        getAllLayers(lyr.GetDown(),res)
        lyr = lyr.GetNext()
    return res


def parseAllObjects(obj,doc,dico_lyr):
    """ fonction récursive pour parcourir les objets
        et leur appliquer le premier calque qui correspond au nom
        (les calques doublons seront ensuite effecés)"""
    while obj:
        lyr = obj.GetLayerObject(doc)
        if lyr:
            lst = dico_lyr[lyr.GetName()]
            if len(lst)>1:
                doc.AddUndo(c4d.UNDOTYPE_CHANGE,obj)
                obj.SetLayerObject(lst[0])
        parseAllObjects(obj.GetDown(),doc,dico_lyr)
        obj = obj.GetNext()

def groupByLayer(lst_obj, doc,parent = None):
    """regroupe la liste d'objet dans un neutre par calque
       si les objet ont une indication de calque"""
    dic = {}
    for obj in lst_obj:
        lyr = obj.GetLayerObject(doc)
        if lyr:
            dic.setdefault(lyr.GetName(),[]).append(obj)
    pred = None
    for name,lst in sorted(dic.items()):
        nullo = c4d.BaseObject(c4d.Onull)
        nullo.SetName(name)
        for o in lst:
            o.InsertUnder(nullo)
        doc.InsertObject(nullo,parent = parent, pred = pred)
        pred = nullo

class ImportDWGgeoref(c4d.plugins.CommandData):
        
    def Execute(self, doc):       
        #le doc doit être en mètres
        doc = c4d.documents.GetActiveDocument()

        usdata = doc[c4d.DOCUMENT_DOCUNIT]
        scale, unit = usdata.GetUnitScale()

        if  unit!= c4d.DOCUMENT_UNIT_M:
            rep = c4d.gui.QuestionDialog(DOC_NOT_IN_METERS_TXT)
            if not rep : return
            unit = c4d.DOCUMENT_UNIT_M
            usdata.SetUnitScale(scale, unit)
            doc[c4d.DOCUMENT_DOCUNIT] = usdata

        fn = c4d.storage.LoadDialog()
        if not fn : return

        if not fn[-4:] == '.dwg':
            c4d.gui.MessageDialog(TXT_NOT_DWG)
            return
        
        #contrôle de la taille du fichier
        #le problème est qu'il faut forcément tout importer avant de voir si c'est géoréférencé
        #et si il y a trop d'éléments C4D rame à mort !'
        size = round(os.path.getsize(fn)/1000000,1)
        if size > ALERT_SIZE_FN:
            rep = c4d.gui.QuestionDialog( f"le fichier dépasse les {ALERT_SIZE_FN}Mo ({size}Mo).\n"\
                                        "Il est conseillé de supprimer tous les calques inutiles avant l'import\n"\
                                        "L'import risque d'être long, voulez-vous vraiment continuer ?")
            if not rep:
                return

        #remise par défaut des options d'importation DWG
        #j'ai eu quelques soucis sur un fichier qund les options étaient en mètre -> à investiguer
        plug = c4d.plugins.FindPlugin(c4d.FORMAT_DWG_IMPORT, c4d.PLUGINTYPE_SCENELOADER)
        if plug is None:
            print ("pas de module d'import DWG")
            return 
        op = {}
        if plug.Message(c4d.MSG_RETRIEVEPRIVATEDATA, op):
            
            import_data = op.get("imexporter",None)
            if not import_data:
                print ("pas de data pour l'import 3Ds")
                return
            
            # Change 3DS import settings
            scale = import_data[c4d.DWGFILTER_SCALE]
            scale.SetUnitScale(1,c4d.DOCUMENT_UNIT_CM)
            import_data[c4d.DWGFILTER_SCALE] = scale
            import_data[c4d.DWGFILTER_CURVE_SUBDIVISION_FACTOR] = 24
            import_data[c4d.DWGFILTER_KEEP_IGES] = False

        doc.StartUndo()
        first_obj = doc.GetFirstObject()
        c4d.documents.MergeDocument(doc,fn, c4d.SCENEFILTER_OBJECTS|c4d.SCENEFILTER_MERGESCENE, thread=None)
        if doc.GetFirstObject() != first_obj:
            doc.AddUndo(c4d.UNDOTYPE_NEWOBJ,doc.GetFirstObject())

        origine = doc[CONTAINER_ORIGIN]

        res = c4d.BaseObject(c4d.Onull)
        res.SetName(os.path.basename(fn))
        obj_parent = doc.GetFirstObject()
        
        scale_factor = None

        for o in obj_parent.GetChildren():
            clone = o.GetClone()
            #suppression du tag matériau
            tag = clone.GetTag(c4d.Ttexture)
            if tag :
                tag.Remove()
            mg = o.GetMg()
            pos = mg.off

            #Facteur d'échelle : si pas encore défini
            #on regarde la position de l'objet et on calcule en fonction des coordonnées nationales
            if not scale_factor:
                scale_factor = 0.0001
                #c'est un peu une méthode bourrin...
                #je pars de l'échelle de base et je fais chaque fois x10
                #en regardant si les coordonnée du premeir objet entre dans les coordonnées suisses..
                #si i arrive à la fin c'est que 
                for i in range(10):
                    if CH_XMIN < pos.x*scale_factor < CH_XMAX and CH_YMIN < pos.z*scale_factor < CH_YMAX:
                        break
                    scale_factor*=10
                if i == 9:
                    c4d.gui.MessageDialog("Problème d'échelle")
                    return
                #print(scale_factor)   
            pos = pos*scale_factor
            #print(pos)
            if not origine:
                doc[CONTAINER_ORIGIN] = c4d.Vector(pos.x,0,pos.z)
                #print(pos)
                origine = doc[CONTAINER_ORIGIN]
            #mg.off = pos-origine

            if o.CheckType(c4d.Opoint):
                pts = [pt*mg*scale_factor -pos for pt in clone.GetAllPoints()]
                clone.SetAllPoints(pts)
                clone.Message(c4d.MSG_UPDATE)

            mg_clone = c4d.Matrix(off = pos-origine)
            clone.InsertUnderLast(res)
            clone.SetMg(mg_clone)

        doc.InsertObject(res)
        doc.AddUndo(c4d.UNDOTYPE_NEWOBJ,res)
        
        #suppression de l'objet source
        obj_parent.Remove()

        #suppression des calques en double
        dico_lyr = getAllLayers(doc.GetLayerObjectRoot().GetDown())
        #pprint(dico_lyr)

        #parcours de tous les objet et on attribue le premier calque des deux
        parseAllObjects(doc.GetFirstObject(),doc,dico_lyr)

        #suppression des calques à double
        lst_lyr_to_remove = []
        for name,lst in dico_lyr.items():
            if len(lst)>1:
                for lyr in lst[1:]:
                    lst_lyr_to_remove.append(lyr)
        for lyr in  lst_lyr_to_remove:
            doc.AddUndo(c4d.UNDOTYPE_DELETEOBJ,lyr)
            lyr.Remove()
            #print(lyr.GetName())
        #il faut vider le dico sinon il reste rempli d'un appel à l'autre !    
        dico_lyr.clear()

        #regroupement des objets dans un neutre par calques
        groupByLayer(res.GetChildren(), doc,parent = res)

        with localimport(os.path.dirname(__file__)) as importer:
            importer.disable(['generate_trees_from_dwg'])
            import generate_trees_from_dwg as gen_trees
            doc.StartUndo()
            gen_trees.main(doc,res)
            doc.EndUndo()

        doc.EndUndo()
        c4d.EventAdd()

        return True

    


# main
if __name__ == "__main__":
    # Registers the plugin
    c4d.plugins.RegisterCommandPlugin(id=PLUGIN_ID,
                                      str="Importer un dwg géoréf. et générer les arbres 3D selon calques 'arbres' ",
                                      info=0,
                                      help="Si le document est déjà géoréférencé, place la géométrie en fonction, sinon géoréférence le document selon le premier objet trouvé. L'échelle est automatiquement détectée en fonction de la première coordonnée trouvée (valable uniquement en Suisse).",
                                      dat=ImportDWGgeoref(),
                                      icon=None)

# localimport-v1.7.3-blob-mcw79
import base64 as b, types as t, zlib as z; m=t.ModuleType('localimport');
m.__file__ = __file__; blob=b'\
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\
XVw='
exec(z.decompress(b.b64decode(blob)), vars(m)); _localimport=m;localimport=getattr(m,"localimport")
del blob, b, t, z, m;
