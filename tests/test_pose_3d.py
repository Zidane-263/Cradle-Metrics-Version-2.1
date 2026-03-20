import unittest
import numpy as np
from utils.fetal_pose_3d import FetalPose3DConverter

class TestFetalPose3D(unittest.TestCase):

    def setUp(self):
        self.converter = FetalPose3DConverter(scale_factor=1.0)
        self.mock_metrics = {
            'body_parts': {
                'head': {'centroid': (350, 150), 'endpoints': []},
                'abdomen': {'centroid': (400, 200), 'endpoints': []},
                'legs': {
                    'centroid': (450, 250),
                    'endpoints': [(460, 260), (440, 260)]
                }
            },
            'spatial_metrics': {
                'head_aspect_ratio': 0.8
            },
            'geometric_metrics': {
                'flexion_angle': 120,
                'compactness': 0.7
            },
            'pose_label': 'hdvb'
        }

    def test_vertex_generation(self):
        result = self.converter.convert_to_3d(self.mock_metrics)
        
        self.assertIn('vertices', result)
        self.assertIn('connections', result)
        
        # Verify centering (abdomen is at 0,0,0)
        # Find abdomen index
        abd_idx = -1
        # In our implementation, abdomen was added after head
        # Let's check the vertices
        has_origin = False
        for v in result['vertices']:
            if v == [0.0, 0.0, 0.0]:
                has_origin = True
        self.assertTrue(has_origin, "Abdomen centroid should be at the origin")

    def test_skeleton_connections(self):
        result = self.converter.convert_to_3d(self.mock_metrics)
        connections = result['connections']
        
        # Should have at least the primary spine connections
        self.assertGreater(len(connections), 0)
        
        # Verify indices are valid
        num_v = len(result['vertices'])
        for start, end in connections:
            self.assertLess(start, num_v)
            self.assertLess(end, num_v)

    def test_depth_estimation(self):
        result = self.converter.convert_to_3d(self.mock_metrics)
        vertices = result['vertices']
        
        # Head should have non-zero Z due to aspect ratio heuristic
        # Head is typically the first vertex if present
        head_v = vertices[0]
        self.assertNotEqual(head_v[2], 0.0, "Head should have an estimated depth offset")

if __name__ == '__main__':
    unittest.main()
