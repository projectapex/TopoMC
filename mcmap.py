# minecraft map module
import os
import numpy
from pymclevel import mclevel
from pymclevel.materials import materials
from pymclevel.box import BoundingBox
from time import clock
from multiprocessing import Pool
from itertools import product
from random import randint

# constants
sealevel = 64
# headroom is the room between the tallest peak and the ceiling
headroom = 5
maxelev = 128-headroom-sealevel

# each column consists of [x, z, elevval, ...]
# where ... is a block followed by zero or more number-block pairs
# examples:
# [x, y, elevval, 'Stone']
#  - fill everything from 0 to elevval with stone
# [x, y, elevval, 'Dirt', 2, 'Water']
#  - elevval down two levels of water, rest dirt
# [x, y, elevval, 'Stone', 1, 'Dirt', 1, 'Water']
#  - elevval down one level of water, then one level of dirt, then stone
# NB: we currently push 'Stone', randint(5,7) at the front
# so whatever the user originally requested has a thin layer before
# becoming stone all the way down.
def layers(columns):
    blocks = []
    for column in columns:
        x = column.pop(0)
        z = column.pop(0)
        elevval = column.pop(0)
        top = sealevel+elevval
        column.insert(0, 'Stone')
        column.insert(1, randint(5,7))
        while (len(column) > 0 or top > 0):
            # better be a block
            block = column.pop()
            # print 'block is %s' % block
            if (len(column) > 0):
                layer = column.pop()
            else:
                layer = top
            # now do something
            # print 'layer is %d' % layer
            if (layer > 0):
                [blocks.append((x, y, z, block)) for y in xrange(top-layer,top)]
                top -= layer
    setBlocksAt(blocks)
        
# my own setblockat
def setBlockAt(x, y, z, string):
    global arrayBlocks
    arrayKey = '%d,%d' % (x >> 4, z >> 4)
    myBlocks = arrayBlocks[arrayKey].asarray()
    myBlocks[x & 0xf, z & 0xf, y] = materials.materialNamed(string)

# more aggregates
def setBlocksAt(blocks):
    global arrayBlocks
    for block in blocks:
        (x, y, z, string) = block
        arrayKey = '%d,%d' % (x >> 4, z >> 4)
        myBlocks = arrayBlocks[arrayKey].asarray()
        myBlocks[x & 0xf, z & 0xf, y] = materials.materialNamed(string)

# my own setblockdataat
def setBlockDataAt(x, y, z, data):
    global arrayData
    arrayKey = '%d,%d' % (x >> 4, z >> 4)
    myData = arrayData[arrayKey].asarray()
    myData[x & 0xf, z & 0xf, y] = data

# my own setblocksdataat
def setBlocksDataAt(blocks):
    global arrayData
    for block in blocks:
        (x, y, z, data) = block
        arrayKey = '%d,%d' % (x >> 4, z >> 4)
        myData = arrayData[arrayKey].asarray()
        myData[x & 0xf, z & 0xf, y] = data

def populateChunk(key,maxcz):
    #print "key is %s" % (key)
    global world
    start = clock()
    ctuple = key.split(',')
    ocx = int(ctuple[0])
    ocz = int(ctuple[1])
    cz = maxcz-ocx
    cx = ocz
    try:
        world.getChunk(cx, cz)
    except mclevel.ChunkNotPresent:
        world.createChunk(cx, cz)
    chunk = world.getChunk(cx, cz)
    world.compressChunk(cx, cz)
    myBlocks = arrayBlocks[key].asarray()
    myData = arrayData[key].asarray()
    for x, z in product(xrange(16), xrange(16)):
        #chunk.Blocks[x,z] = arrayBlocks[key][15-z,x]
        chunk.Blocks[x,z] = myBlocks[15-z,x]
    #arrayBlocks[key] = None
    if key in arrayData:
        for x, z in product(xrange(16), xrange(16)):
            chunk.Data[x,z] = myData[15-z,x]
        #arrayData[key] = None
    chunk.chunkChanged(False)
    return (clock()-start)

def populateChunkstar(args):
    return populateChunk(*args)

def populateWorld(processes):
    global world
    allkeys = numpy.array([list(key.split(',')) for key in arrayBlocks.keys()])
    maxcz = int(max(allkeys[:,1]))
    # FIXME: still no multiprocessing support but less important
    if (processes == 1 or True):
        times = [populateChunk(key,maxcz) for key in arrayBlocks.keys()]
    else:
        pool = Pool(processes)
        tasks = [(key,maxcz) for key in arrayBlocks.keys()]
        results = pool.imap_unordered(populateChunkstar, tasks)
        times = [x for x in results]
    count = len(times)
    print '%d chunks written (average time %.2f seconds)' % (count, sum(times)/count)

def checkWorld(string):
    if (string == None):
        argparse.error("a world must be defined")
    try:
        worldNum = int(string)
    except ValueError:
        if not os.path.exists(string):
            os.mkdir(string)
        if not os.path.isdir(string):
            raise IOError, "%s already exists" % string
        level = mclevel.MCInfdevOldLevel(string, create=True)
        level.saveInPlace()
        level = None
        return string
    else:
        if 1 < worldNum <= 5:
            string = worldNum
        else:
            raise IOError, "bad value for world: %s" % string
    return string

def initWorld(string):
    "Open this world."
    global world
    try:
        worldNum = int(string)
    except ValueError:
        myworld = mclevel.MCInfdevOldLevel(string, create=True)
    else:
        myworld = mclevel.loadWorldNumber(worldNum)
    return myworld

def saveWorld(spawn):
    global world
    sizeOnDisk = 0
    # incoming spawn is in xzy
    # adjust it to sealevel, and then up another two for good measure
    spawnxyz = (spawn[0], spawn[2]+sealevel+2, spawn[1])
    world.setPlayerPosition(spawnxyz)
    world.setPlayerSpawnPosition(spawnxyz)
    # stolen from pymclevel/mce.py
    for i, cPos in enumerate(world.allChunks, 1):
        ch = world.getChunk(*cPos);
        sizeOnDisk += ch.compressedSize();
    world.SizeOnDisk = sizeOnDisk
    world.saveInPlace()

# variables
arrayBlocks = {}
arrayData = {}

