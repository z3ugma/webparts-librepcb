
from typing import List, NamedTuple, Tuple, Callable
from librepcb_parts_generator.entities.common import Position
from librepcb_parts_generator.entities.package import Polygon

class AlignmentReference(NamedTuple):
    """Represents a reference point for alignment."""
    source_x: float  # Pixel position in PNG
    source_y: float  # Pixel position in PNG
    target_x: float  # Physical position in mm
    target_y: float  # Physical position in mm
    label: str       # A descriptive label, e.g., "V1" for Vertex 1

class FootprintAlignment(NamedTuple):
    """Container for footprint alignment data."""
    reference_points: List[AlignmentReference]

class AlignmentCalculator:
    """
    Calculates alignment references by mapping polygon vertices in mm-space
    back to pixel-space on the rendered PNG.
    """
    def calculate_alignment_from_polygon(
        self,
        polygon: Polygon,
        coordinate_mapper: Callable[[float, float], Tuple[float, float]],
    ) -> FootprintAlignment:
        """
        Calculate alignment data using the vertices of a package outline polygon.

        Args:
            polygon: The polygon object for the package outline (in mm).
            coordinate_mapper: A function that converts (mm_x, mm_y) to (png_x, png_y).

        Returns:
            A FootprintAlignment object with two reference points.
        """
        if len(polygon.vertices) < 2:
            raise ValueError("Polygon must have at least 2 vertices for alignment.")

        v1_index, v2_index = self._select_optimal_reference_vertices(polygon.vertices)
        
        v1 = polygon.vertices[v1_index].position
        v2 = polygon.vertices[v2_index].position

        # Convert the selected millimeter-based vertices to PNG pixel coordinates
        png_x1, png_y1 = coordinate_mapper(v1.x, v1.y)
        png_x2, png_y2 = coordinate_mapper(v2.x, v2.y)

        # Create the two reference points
        # Note: The target_y is inverted to match LibrePCB's Y-up coordinate system.
        ref1 = AlignmentReference(
            source_x=png_x1,
            source_y=png_y1,
            target_x=v1.x,
            target_y=-v1.y,
            label=f"V{v1_index + 1}"
        )
        ref2 = AlignmentReference(
            source_x=png_x2,
            source_y=png_y2,
            target_x=v2.x,
            target_y=-v2.y,
            label=f"V{v2_index + 1}"
        )

        return FootprintAlignment(reference_points=[ref1, ref2])

    def _select_optimal_reference_vertices(self, vertices: List[Position]) -> Tuple[int, int]:
        """
        Selects the two vertices that are the furthest apart.

        Returns:
            A tuple containing the indices of the two most distant vertices.
        """
        max_dist_sq = -1
        v1_idx, v2_idx = -1, -1

        for i in range(len(vertices)):
            for j in range(i + 1, len(vertices)):
                p1 = vertices[i].position
                p2 = vertices[j].position
                dist_sq = (p2.x - p1.x)**2 + (p2.y - p1.y)**2
                if dist_sq > max_dist_sq:
                    max_dist_sq = dist_sq
                    v1_idx, v2_idx = i, j
        
        if v1_idx == -1 or v2_idx == -1:
            raise ValueError("Could not determine optimal vertices from the provided list.")

        return v1_idx, v2_idx
