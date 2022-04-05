# -*- coding: utf-8 -*-

import c4d
from libs import shapefile
import os
from random import randint
from math import pi

# Script state in the menu or the command palette
# Return True or c4d.CMD_ENABLED to enable, False or 0 to disable
# Alternatively return c4d.CMD_ENABLED|c4d.CMD_VALUE to enable and check/mark
# def state():
#    return True

CONTAINER_ORIGIN = 1026473

NOM_FICHIER_ARBRES = '__arbres_2018__.c4d'

ID_CLONER = 1018544
ID_TAG_INFLUENCE_MOGRAPH = 440000231
ID_PLAIN_EFFECTOR = 1021337
ID_RANDOM_EFFECTOR = 1018643

NOM_OBJ_POINTS = "arbres"
NOM_CLONER = NOM_OBJ_POINTS + "_cloneur"
NOM_TAG_DIAMETRES = "diametres"
NOM_TAG_HAUTEURS = "hauteurs"
NOM_POINT_OBJECT = "points_" + NOM_OBJ_POINTS
NOM_EFFECTOR_DIAMETRES = "effecteur_" + NOM_TAG_DIAMETRES
NOM_EFFECTOR_HAUTEURS = "effecteur_" + NOM_TAG_HAUTEURS
NOM_EFFECTOR_RANDOM = "effecteur_rotation_aleatoire"
NULL_NAME = NOM_OBJ_POINTS

HAUT_SRCE = 10.  # on part avec une source qui fait 10m de haut
DIAM_SRCE = 10.  # idem pour le diametre

FACTEUR_HAUT = 1.
FACTEUR_DIAMETRE = 1.


def create_point_object(points):
    res = c4d.PolygonObject(len(points), 0)
    res.SetAllPoints(points)
    res.Message(c4d.MSG_UPDATE)
    return res


def create_effector(name, select=None, typ=ID_PLAIN_EFFECTOR):
    res = c4d.BaseObject(typ)
    res.SetName(name)
    if select:
        res[c4d.ID_MG_BASEEFFECTOR_SELECTION] = select
    return res


def create_mograph_cloner(doc, points, hauteurs, diametres, objs_srces, centre=None, name=None):
    # tag = doc.GetActiveTag()
    # return

    res = c4d.BaseObject(c4d.Onull)
    if not name: name = NULL_NAME
    res.SetName(name)

    if centre:
        creerGeoTag(res, doc, centre)

    poly_o = create_point_object(points)
    poly_o.SetName(NOM_POINT_OBJECT)

    cloner = c4d.BaseObject(ID_CLONER)
    cloner.SetName(NOM_CLONER)
    cloner[c4d.ID_MG_MOTIONGENERATOR_MODE] = 0  # mode objet
    cloner[c4d.MG_OBJECT_LINK] = poly_o
    cloner[c4d.MG_POLY_MODE_] = 0  # mode point
    cloner[c4d.MG_OBJECT_ALIGN] = False
    cloner[c4d.MGCLONER_VOLUMEINSTANCES_MODE] = 2  # multiinstances
    cloner[c4d.MGCLONER_MODE] = 2  # repartition aleatoire des clones

    # insertion des objets source
    if objs_srces:
        for o in objs_srces.GetChildren():
            clone = o.GetClone()
            clone.InsertUnderLast(cloner)

    tagHauteurs = c4d.BaseTag(440000231)
    cloner.InsertTag(tagHauteurs)
    tagHauteurs.SetName(NOM_TAG_HAUTEURS)
    # ATTENTION bien mettre des float dans la liste sinon cela ne marche pas !
    scale_factor_haut = lambda x: float(x) / HAUT_SRCE - 1.
    c4d.modules.mograph.GeSetMoDataWeights(tagHauteurs, [scale_factor_haut(h) for h in hauteurs])
    # tagHauteurs.SetDirty(c4d.DIRTYFLAGS_DATA) #plus besoin depuis la r21 !

    tagDiametres = c4d.BaseTag(440000231)
    cloner.InsertTag(tagDiametres)
    tagDiametres.SetName(NOM_TAG_DIAMETRES)
    scale_factor_diam = lambda x: float(x * 2) / DIAM_SRCE - 1.
    c4d.modules.mograph.GeSetMoDataWeights(tagDiametres, [scale_factor_diam(d) for d in diametres])
    # tagDiametres.SetDirty(c4d.DIRTYFLAGS_DATA) #plus besoin depuis la r21 !

    # Effecteur simple hauteurs
    effector_heights = create_effector(NOM_EFFECTOR_HAUTEURS, select=tagHauteurs.GetName())
    effector_heights[c4d.ID_MG_BASEEFFECTOR_POSITION_ACTIVE] = False
    effector_heights[c4d.ID_MG_BASEEFFECTOR_SCALE_ACTIVE] = True
    effector_heights[c4d.ID_MG_BASEEFFECTOR_SCALE, c4d.VECTOR_Y] = FACTEUR_HAUT

    # Effecteur simple diametres
    effector_diam = create_effector(NOM_EFFECTOR_DIAMETRES, select=tagDiametres.GetName())
    effector_diam[c4d.ID_MG_BASEEFFECTOR_POSITION_ACTIVE] = False
    effector_diam[c4d.ID_MG_BASEEFFECTOR_SCALE_ACTIVE] = True
    effector_diam[c4d.ID_MG_BASEEFFECTOR_SCALE] = c4d.Vector(FACTEUR_DIAMETRE, 0, FACTEUR_DIAMETRE)

    # Effecteur random
    effector_random = create_effector(NOM_EFFECTOR_RANDOM, typ=ID_RANDOM_EFFECTOR)
    effector_random[c4d.ID_MG_BASEEFFECTOR_POSITION_ACTIVE] = False
    effector_random[c4d.ID_MG_BASEEFFECTOR_ROTATE_ACTIVE] = True
    effector_random[c4d.ID_MG_BASEEFFECTOR_ROTATION, c4d.VECTOR_X] = pi * 2

    ie_data = cloner[c4d.ID_MG_MOTIONGENERATOR_EFFECTORLIST]
    ie_data.InsertObject(effector_heights, 1)

    ie_data.InsertObject(effector_diam, 1)
    ie_data.InsertObject(effector_random, 1)
    cloner[c4d.ID_MG_MOTIONGENERATOR_EFFECTORLIST] = ie_data

    cloner.Message(c4d.MSG_UPDATE)
    cloner.InsertUnder(res)
    effector_heights.InsertUnder(res)
    effector_diam.InsertUnder(res)
    effector_random.InsertUnder(res)
    poly_o.InsertUnder(res)

    doc.InsertObject(res)
    doc.AddUndo(c4d.UNDOTYPE_NEW, res)

    effector_heights.Message(c4d.MSG_MENUPREPARE, doc)
    effector_diam.Message(c4d.MSG_MENUPREPARE, doc)
    effector_random.Message(c4d.MSG_MENUPREPARE, doc)

    return


# Main function
def main():
    print(randint(0,100))
    mg = op.GetMg()
    pts = [p*mg for p in op.GetAllPoints()]
    hauteurs = [randint(1500,1500)/100 for i in range(len(pts))]
    diametres = [randint(300,500)/100 for i in range(len(pts))]
    srce_veget = doc.SearchObject('arbres_cloneur')

    create_mograph_cloner(doc, pts, hauteurs, diametres, srce_veget,name = 'arbres_test')
    c4d.EventAdd()


# Execute main()
if __name__ == '__main__':
    # fn = '/Users/donzeo/Documents/TEMP/NYON_SPLA/C4D/arbres_script.shp'
    # fn = '/Users/donzeo/Documents/TEMP/NYON_SPLA/test_arbre.shp'
    main()