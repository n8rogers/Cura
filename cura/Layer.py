from .LayerPolygon import LayerPolygon

from UM.Math.Vector import Vector
from UM.Mesh.MeshBuilder import MeshBuilder

import numpy

class Layer:
    def __init__(self, layer_id):
        self._id = layer_id
        self._height = 0.0
        self._thickness = 0.0
        self._polygons = []
        self._element_count = 0

    @property
    def height(self):
        return self._height

    @property
    def thickness(self):
        return self._thickness

    @property
    def polygons(self):
        return self._polygons

    @property
    def elementCount(self):
        return self._element_count

    def setHeight(self, height):
        self._height = height

    def setThickness(self, thickness):
        self._thickness = thickness

    def lineMeshVertexCount(self):
        result = 0
        for polygon in self._polygons:
            result += polygon.lineMeshVertexCount()

        return result

    def lineMeshElementCount(self):
        result = 0
        for polygon in self._polygons:
            result += polygon.lineMeshElementCount()

        return result

    def build(self, vertex_offset, index_offset, vertices, colors, indices):
        result_vertex_offset = vertex_offset
        result_index_offset = index_offset
        self._element_count = 0
        for polygon in self._polygons:
            polygon.build(result_vertex_offset, result_index_offset, vertices, colors, indices)
            result_vertex_offset += polygon.lineMeshVertexCount()
            result_index_offset += polygon.lineMeshElementCount()
            self._element_count += polygon.elementCount

        return (result_vertex_offset,result_index_offset)

    def createMesh(self):
        return self.createMeshOrJumps(True)

    def createJumps(self):
        return self.createMeshOrJumps(False)

    def createMeshOrJumps(self, make_mesh):
        builder = MeshBuilder() # This is never really used, only the mesh_data inside
        index_pattern = numpy.array([[0,3,2,0,1,3]],dtype = numpy.int32 )
        
        line_count = 0
        if make_mesh:
            for polygon in self._polygons:
                line_count += polygon._mesh_line_count
        else:
            for polygon in self._polygons:
                line_count += polygon._jump_count
            
        
        # Reserve the neccesary space for the data upfront
        builder.reserveFaceAndVerticeCount( 2*line_count, 4*line_count )
        
        for polygon in self._polygons:
            #if make_mesh and (polygon.type == LayerPolygon.MoveCombingType or polygon.type == LayerPolygon.MoveRetractionType):
            #    continue
            #if not make_mesh and not (polygon.type == LayerPolygon.MoveCombingType or polygon.type == LayerPolygon.MoveRetractionType):
            #    continue
            
            index_mask = numpy.logical_not(polygon._jump_mask) if make_mesh else polygon._jump_mask

            # Create an array with rows [p p+1] and only save those we whant to draw based on make_mesh
            points = numpy.concatenate((polygon.data[:-1],polygon.data[1:]),1)[index_mask.ravel()]
            # Line types of the points we want to draw
            line_types = polygon._types[index_mask]
            
          
            #if polygon.type == LayerPolygon.InfillType or polygon.type == LayerPolygon.SkinType or polygon.type == LayerPolygon.SupportInfillType:
            #    points[:,1] -= 0.01
            #if polygon.type == LayerPolygon.MoveCombingType or polygon.type == LayerPolygon.MoveRetractionType:
            #    points[:,1] += 0.01
            # Shift the z-axis according to previous implementation. 
            if make_mesh:
                points[polygon._orInfillSkin[line_types],1::3] -= 0.01
            else:
                points[:,1::3] += 0.01

            # Create an array with normals and tile 2 copies to match size of points variable
            normals = numpy.tile( polygon.getNormals()[index_mask.ravel()], (1,2))

            # Scale all normals by the line width of the current line so we can easily offset.
            normals *= (polygon.lineWidths[index_mask.ravel()] / 2)

            # Create 4 points to draw each line segment, points +- normals results in 2 points each. Reshape to one point per line
            f_points = numpy.concatenate((points-normals,points+normals),1).reshape((-1,3))
            # index_pattern defines which points to use to draw the two faces for each lines egment, the following linesegment is offset by 4 
            f_indices = ( index_pattern + numpy.arange(0,4*len(normals),4,dtype=numpy.int32).reshape((-1,1)) ).reshape((-1,3))
            f_colors = numpy.repeat(polygon._color_map[line_types], 4, 0)

            builder.addFacesWithColor(f_points, f_indices, f_colors)

        
        return builder.build()