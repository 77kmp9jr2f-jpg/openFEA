from typing import Literal, Annotated
from pydantic import BaseModel, Field, ConfigDict, model_validator
import math

Number = Annotated[float, Field(allow_inf_nan=False)]
Vec3 = tuple[Number, Number, Number]

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Feature(StrictModel):
    operation: Literal['add', 'cut'] = 'add'
    primitive: Literal['box', 'cylinder'] = 'box'
    origin: Vec3 = (0, 0, 0)
    size: Vec3 = (10, 10, 10)
    axis: Vec3 = (0, 0, 10)
    radius: Number = Field(default=5, gt=0, le=1000)

    @model_validator(mode='after')
    def valid_feature(self):
        if any(abs(n) > 2000 for n in (*self.origin, *self.size, *self.axis)):
            raise ValueError('Feature coordinates must be within 2,000 mm.')
        if self.primitive == 'box' and min(self.size) <= 0:
            raise ValueError('Box dimensions must be positive.')
        if self.primitive == 'cylinder' and math.dist(self.axis, (0,0,0)) < 0.01:
            raise ValueError('Cylinder axis must have a positive length.')
        return self

class Geometry(StrictModel):
    name: str = Field(default='Mounting bracket', max_length=120)
    kind: Literal['bracket', 'plate', 'shaft', 'custom', 'step'] = 'bracket'
    length: Number = Field(default=80, ge=2, le=1000)
    width: Number = Field(default=40, ge=2, le=1000)
    height: Number = Field(default=60, ge=2, le=1000)
    thickness: Number = Field(default=8, ge=0.5, le=300)
    hole_diameter: Number = Field(default=8, ge=0, le=300)
    mesh_size: Number = Field(default=7, ge=0.5, le=100)
    features: list[Feature] = Field(default_factory=list, max_length=32)
    step_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')
    provenance: Literal['demo', 'user_dimensions', 'image_proposal', 'step_import'] = 'user_dimensions'
    assumptions: list[str] = Field(default_factory=list, max_length=30)

    @model_validator(mode='after')
    def geometry_checks(self):
        if self.kind == 'bracket' and self.thickness >= min(self.length,self.height)/2:
            raise ValueError('Bracket thickness must be less than half the length and height.')
        if self.kind in ('bracket','plate') and self.hole_diameter >= min(self.length,self.width)/3:
            raise ValueError('Hole diameter must be less than a third of the length and width.')
        if self.kind == 'shaft' and self.hole_diameter >= self.width:
            raise ValueError('Bore diameter must be smaller than shaft diameter (width).')
        if self.kind == 'custom' and (not self.features or self.features[0].operation != 'add'):
            raise ValueError('A custom solid must begin with an additive feature.')
        if self.kind == 'step' and not self.step_id:
            raise ValueError('Choose a STEP file first.')
        return self

class Material(StrictModel):
    name: str = Field(default='Aluminum · illustrative', max_length=100)
    young_mpa: Number = Field(default=69000, gt=0, le=1e7)
    poisson: Number = Field(default=0.33, gt=-0.9, lt=0.49)
    yield_mpa: Number = Field(default=240, gt=0, le=1e5)
    density_kg_m3: Number = Field(default=2700, gt=0, le=50000)

class Force(StrictModel):
    face_id: int = Field(gt=0)
    vector: Vec3 = (0,0,-100)
    @model_validator(mode='after')
    def valid_force(self):
        if not 1e-9 < math.dist(self.vector,(0,0,0)) <= 1e8:
            raise ValueError('Force magnitude must be positive and at most 100 MN.')
        return self

class Analysis(StrictModel):
    model_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    material: Material = Field(default_factory=Material)
    fixed_faces: list[int] = Field(min_length=1,max_length=50)
    loads: list[Force] = Field(min_length=1,max_length=20)
    notes: str = Field(default='',max_length=12000)
    confirmed: bool = False
    reference_id: str | None = Field(default=None,pattern=r'^[a-f0-9]{32}$')
    annotations: list['Annotation'] = Field(default_factory=list,max_length=100)
    @model_validator(mode='after')
    def validate_setup(self):
        if not self.confirmed:
            raise ValueError('Confirm geometry, material and boundary conditions before solving.')
        if set(self.fixed_faces) & {load.face_id for load in self.loads}:
            raise ValueError('A face cannot be both fully fixed and loaded.')
        return self

class Annotation(StrictModel):
    id: str = Field(max_length=80)
    tool: Literal['arrow','rectangle','note','dimension']
    start: tuple[Number,Number]
    end: tuple[Number,Number]
    text: str = Field(default='',max_length=1000)

class ImageInput(StrictModel):
    name: str = Field(default='Reference image',max_length=160)
    data_url: str = Field(max_length=16_000_000)

class AssistantRequest(StrictModel):
    message: str = Field(min_length=1,max_length=16000)
    image_id: str | None = Field(default=None,pattern=r'^[a-f0-9]{32}$')
    annotations: list[Annotation] = Field(default_factory=list,max_length=100)
    geometry: Geometry | None = None
    history: list[dict[str,str]] = Field(default_factory=list,max_length=12)
    model_id: str | None = Field(default=None,pattern=r'^[a-f0-9]{32}$')
    material: Material | None = None
    fixed_faces: list[int] = Field(default_factory=list,max_length=50)
    loads: list[Force] = Field(default_factory=list,max_length=20)
    application_notes: str = Field(default='',max_length=12000)
    run_id: str | None = Field(default=None,pattern=r'^[a-f0-9]{32}$')

class Study(StrictModel):
    name: str = Field(max_length=120)
    state: dict

Analysis.model_rebuild()

class GPUSolution(StrictModel):
    system_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    displacement: list[Number] = Field(min_length=1,max_length=150000)
    device: str = Field(min_length=1,max_length=200)
    iterations: int = Field(ge=1,le=20000)
    refinements: int = Field(ge=1,le=10)
    seconds: Number = Field(ge=0,le=600)
