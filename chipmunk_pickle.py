class ChipmunkPickle():
    def __init__(self, holes, hole_arguments, constraints, num_fields_in_prog,
                 num_state_groups, num_state_slots):
        self.holes_ = holes
        self.hole_arguments_ = hole_arguments
        self.constraints_ = constraints
        self.num_fields_in_prog_ = num_fields_in_prog
        self.num_state_groups_ = num_state_groups
        self.num_state_slots_  = num_state_slots
