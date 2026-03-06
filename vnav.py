class WP:
    '''
    A WP class represnts a single waypoint of a flight plan. It is definted by its name and altitude constraints, and the distance to the waypoint from the previous waypoint.
    WP class methods:
        - __str__: Provides a formatted string representation of the wp: waypoint, distance, and altitude constraints.
        - meets_constraints: Checks if a given altitude meets the wp's altitude constraints.
        - calculate_TOD: Calculates the distance to the Top of Descent (TOD) based gradient and starting altitude.
        - calculate_gradient: Calculates the descent gradient based on the starting altitude and distance to the waypoint
    '''
    def __init__(self, name, distance, above, below, speed):
        self.name = name
        self.distance = distance
        self.above = above
        self.below = below
        self.speed = speed
        self.gradient = DEFAULT_GRADIENT
        self.grad_based_on = 0 # cumulative distance to the WP that the descent gradient is based on
        self.cum_dis = 0
        self.crossing_altitude = self.above
        self.gen_constraint_str()

    def __str__(self):
        return f"{self.name}\t{self.constraint_str}\t{self.distance:.1f} nm\t{self.speed} kts"
        
    def meets_constraints(self, altitude):
        # Check if a given altitude meets the waypoint's altitude constraints.
        return self.above <= altitude <= self.below
    
    def calculate_TOD(self, start_altitude):
        '''
        Calculate the distance for Top of Descent (TOD) to the WP's computed crossing altitude based on a given starting altitude.
        '''
        self.TOD_distance = (start_altitude - self.crossing_altitude) / self.gradient # Distance to TOD in nm

        if self.distance < self.TOD_distance:
            #print(f"WARNING: Required TOD distance for {self.gradient:.0f} ft/nm descent ({self.TOD_distance:.1f} nm) to {self.crossing_altitude:.0f} ft exceeds distance to waypoint ({self.distance:.1f} nm).")
            self.calculate_gradient(start_altitude, self.distance, self.crossing_altitude)
            self.TOD_distance = self.distance
            #print(f"Required gradient for descent from current position: {self.gradient:.0f} ft/nm")
        else:
            pass
            #print(f"TOD distance from {self.name} for {self.gradient:.0f} ft/nm descent to {self.crossing_altitude:.0f} ft: {self.TOD_distance:.1f} nm")
            
    def calculate_gradient(self, start_altitude, distance, end_altitude):
        '''
        Calculate the descent gradient based on the starting altitude and the distance to the waypoint.
        '''
        self.gradient = (start_altitude - end_altitude) / distance # Descent gradient in ft/nm

    def backcalc_altitude_at_distance(self, start_altitude, distance):
        '''
        Calculate the altitude at a given distance along the descent path based on the starting altitude and the descent gradient.
        Adding gradient * distance because we are calculating backwards up the descent path from the waypoint to the cruise altitude.
        '''
        return start_altitude + self.gradient * distance
    
    def gen_constraint_str(self):
        if self.above == 0 and self.below == 99999:
            self.constraint_str = ""
        elif self.below == 99999:
            self.constraint_str = f"{self.above}A"
        elif self.above == 0:
            self.constraint_str = f"{self.below}B"
        elif self.above == self.below:
            self.constraint_str = f"{self.above}"
        else:
            self.constraint_str = f"{self.above}A {self.below}B"

    def calculate_vertical_speed(self):
        '''
        Calculate the required vertical speed to meet the descent gradient based on a given ground speed.
        '''
        self.vertical_speed = self.gradient * self.speed / 60 # Vertical speed in ft/min (1 nm = 6073 ft, speed is in kts, so divide by 60 to get minutes)

class FlightPlan:
    def __init__(self):
        if TEST_MODE:
            # Initialize with test waypoints            
            self.cruise_altitude = TEST_ALTITUDE
            self.cruise_speed = TEST_SPEED
            self.wps = TEST_FP
            print(f"Initializing test flight plan with {len(self)} predefined waypoints and cruise altitude {self.cruise_altitude} ft and cruise speed {self.cruise_speed} kts.\n")
            self.print_wps()
        else:
            self.enter_cruise_altitude()
            self.enter_cruise_speed()
            self.wps = []

            cont = 'y'
            while cont.lower() == 'y':
                self.enter_wps()
                self.print_wps()
                cont = input("Do you want to add more wps? (y/n): ")
    
        self.update_cumulative_distances()
        self.clean_constraints()
        self.compute_profile()
        self.compute_TOD()
        self.compute_vertical_speeds()
        self.print_descent_profile()
    
    def __len__(self):
        # Return the number of waypoints in the flight plan.
        return len(self.wps)
    
    def enter_cruise_altitude(self):
        '''
        Take user input for cruise altitude.
        '''
        while True:
            cruise_altitude = input("Enter Cruise Altitude (ft): ")
            if not cruise_altitude:
                print("Cruise altitude is required. Please enter a valid altitude.")
            else:
                self.cruise_altitude = int(cruise_altitude)
                print(f"Cruise altitude set to {self.cruise_altitude} ft.")
                return
            
    def enter_cruise_speed(self):
        '''
        Take user input for cruise speed.
        '''
        while True:
            cruise_speed = input("Enter Cruise Speed (kts): ")
            if not cruise_speed:
                print("Cruise speed is required. Please enter a valid speed.")
            else:
                self.cruise_speed = int(cruise_speed)
                print(f"Cruise speed set to {self.cruise_speed} kts.")
                return
    
    def enter_wps(self):
        '''
        Take user inputs for flightplan wps.
        '''
        print("\nLeg Entry: add waypoints in order, starting backwards from the destination.")
        print("For example, if your flight plan is: ORIGIN -> WP1 -> WP2 -> DESTINATION, enter the waypoints in this order: DESTINATION, WP2, WP1, ORIGIN.")
        print("*** A blank waypoint name will terminate flight plan entry.\n")

        while True:
            name = input("Waypoint Name: ")
            if not name: # A blank waypoint name indicates the end of flight plan entry.
                print("Leg entry terminated.\n")
                return
            else:
                above = input(f"Cross {name} AT OR ABOVE (ft): ")
                if not above:
                    above = 0
                else:
                    above = int(above)

                below = input(f"Cross {name} AT OR BELOW (ft): ")
                if not below:
                    below = 99999
                else:
                    below = int(below)

                distance = input(f"Distance to {name} (nm): ")
                if not distance:
                    distance = 999
                else:
                    distance = float(distance)

                speed = input(f"Ground Speed to {name} (kts): ")
                if not speed:
                    speed = self.cruise_speed
                else:
                    speed = float(speed)

                self.wps.append(WP(name, distance, above, below, speed))
            print("")

    def print_wps(self):
        print("FLIGHT PLAN WAYPOINTS:")
        print("WP\tConst\tDis\tGS")
        for wp in self.wps:
            print(wp)
        print("")
        return
    
    def update_cumulative_distances(self):
        '''
        Update the cumulative distance for each wp in the flight plan.
        This is necessary for calculating the distance to TOD from the cruise altitude.
        '''
        #print("Updating cumulative distances for each wp:")
        cum_dis = 0
        for wp in self.wps:
            wp.cum_dis = cum_dis
            cum_dis += wp.distance            
            #print(f"Cumulative distance to {wp.name}: {wp.cum_dis:.1f} nm")
        #print("")

    def clean_constraints(self):
        """If any WP has an ABOVE constraints above the cruise altitude, remove all constraints from that WP."""
        for wp in self.wps:
            if wp.above > self.cruise_altitude:
                wp.above = 0
                wp.below = 99999
                wp.gen_constraint_str()

    def compute_profile(self):
        '''
        Compute the descent profile for the flight plan.
        '''
        for i, wp in enumerate(self.wps):

            # Check if the descent path meets the constraints of the next wps.
            for test_wp in self.wps[i+1:]:
                if wp.grad_based_on > 0 and test_wp.cum_dis > wp.grad_based_on:
                    # If the wp already has a descent gradient constrained by an earlier waypoint, we do not need to keep checking aginst the next waypoint's constraints.
                    pass
                else:
                     # Calculate crossing altitude for the next wp based on the descent gradient and distance to the next wp.
                    distance = test_wp.cum_dis - wp.cum_dis # Distance from current wp to next wp in nm                   
                    test_wp.crossing_altitude = wp.backcalc_altitude_at_distance(wp.crossing_altitude, distance)

                    # If the calculated crossing altitude for the next wp is above the cruise altitude, we'll just stay in cruise mode.
                    # Set it crossing altitude to the cruise altitude and set the descent gradient to 0.
                    if test_wp.crossing_altitude > self.cruise_altitude:   
                        test_wp.crossing_altitude = self.cruise_altitude
                        test_wp.gradient = 0

                    #print(f"From {wp.name} to {test_wp.name}: Starting at {wp.crossing_altitude:.0f} ft for {distance:0.1f} nm at {wp.gradient:.0f} ft/nm: {test_wp.crossing_altitude:.0f} ft")

                    if test_wp.meets_constraints(test_wp.crossing_altitude):
                        pass
                        #print(f"Crossing altitude for {test_wp.name} meets constraints: {test_wp.above}A {test_wp.below}B\n")
                    else:
                        #print(f"WARNING: Crossing altitude for {test_wp.name} does NOT meet constraints: {test_wp.above}A {test_wp.below}B\n")
                        # Set the crossing altitude to the closest constraint if it does not meet constraints.
                        if test_wp.crossing_altitude < test_wp.above:
                            test_wp.crossing_altitude = test_wp.above
                        elif test_wp.crossing_altitude > test_wp.below:
                            test_wp.crossing_altitude = test_wp.below

                        # Recalculate the descent gradient for current wp based on the new crossing altitude and distance to the next wp.
                        wp.calculate_gradient(test_wp.crossing_altitude, distance, wp.crossing_altitude)
                        #print(f"New descent gradient for {wp.name} based on crossing {test_wp.name} at {test_wp.crossing_altitude} ft: {wp.gradient:.0f} ft/nm\n")
                        wp.grad_based_on = test_wp.cum_dis

                        self.compute_profile()

    def compute_TOD(self):
        '''
        1) Find the "Top WP", which is the last WP that has a crossing altitude < cruising altitude.
            Note: Might not be the last WP in the flight plan.
        2) Compute the TOD distance from the Top WP'''
        for wp in self.wps:
            if wp.crossing_altitude < self.cruise_altitude:
                self.top_wp = wp
        
        self.top_wp.gradient = DEFAULT_GRADIENT
        self.top_wp.calculate_TOD(self.cruise_altitude)
        self.top_wp.calculate_vertical_speed()
    
    def compute_vertical_speeds(self):
        for wp in self.wps:
            wp.calculate_vertical_speed()

    def print_descent_profile(self):
        print("***Cruise Profile***")
        print(f"Cruise Altitude: {self.cruise_altitude} ft")
        print(f"Cruise Speed: {self.cruise_speed} kts")
        print(f"TOD distance from {self.top_wp.name} for {self.top_wp.vertical_speed} ft/min descent to {self.top_wp.crossing_altitude:.0f} ft: {self.top_wp.TOD_distance:.1f} nm\n")

        print("*** Descent Profile ***")
        print("TO WP\tALT\tVSR\tGS")           
        for wp in reversed(self.wps): # Print the descent profile from the first WP to the destination WP.
            if wp.gradient == 0:
                grad_str = "Level"
                vs_str = "Level"
            else:
                grad_str = f"{wp.gradient:.0f}"
                vs_str = f"{wp.vertical_speed:.0f}"
            #print(f"{vs_str} at {wp.speed} kts GS to cross {wp.name} at {wp.crossing_altitude:.0f} ft. (Gradient: {grad_str})")
           
            print(f"{wp.name}\t{wp.crossing_altitude:.0f}\t{vs_str}\t{wp.speed}")
        print("")

DEFAULT_GRADIENT = 330 # ft/nm, typical for a 3 degree glide path
TEST_MODE = True
TEST_FP = [
                WP("TRNDO", 7, 5000, 5000, 210),
                WP("SLI", 8, 7000, 7000, 210),
                WP("BUFIE", 4, 0, 8000, 210),
                WP("ZAPPP", 11, 9000, 99999, 210),
                WP("SHHOW", 7, 12000, 12000, 280),
                WP("PHUNN", 18, 14000, 14000, 280),
                WP("DIRBY", 15, 0, 99999, 280),
                WP("GOATZ", 63, 16000, 16000, 280)
            ]
TEST_ALTITUDE = 22000
TEST_SPEED = 280

fp = FlightPlan()