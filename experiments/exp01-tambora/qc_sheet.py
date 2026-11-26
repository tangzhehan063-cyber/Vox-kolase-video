import sys
from PIL import Image
def sheet(items, out, bg=(60,110,200), cols=4, cell=520):
    rows=(len(items)+cols-1)//cols
    S=Image.new("RGB",(cols*cell,rows*cell),bg)
    for i,(n,im) in enumerate(items):
        im=im.copy(); im.thumbnail((cell-20,cell-20))
        S.paste(im,((i%cols)*cell+(cell-im.width)//2,(i//cols)*cell+(cell-im.height)//2),im)
    S.save(out)
