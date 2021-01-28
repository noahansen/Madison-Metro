from math import sin, cos, asin, sqrt, pi
import pandas as pd
from zipfile import ZipFile
from datetime import datetime
from time import time

def haversine_miles(lat1, lon1, lat2, lon2):
    """Calculates the distance between two points on earth using the
    harversine distance (distance between points on a sphere)
    See: https://en.wikipedia.org/wiki/Haversine_formula

    :param lat1: latitude of point 1
    :param lon1: longitude of point 1
    :param lat2: latitude of point 2
    :param lon2: longitude of point 2
    :return: distance in miles between points
    """
    lat1, lon1, lat2, lon2 = (a/180*pi for a in [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon/2) ** 2
    c = 2 * asin(min(1, sqrt(a)))
    d = 3956 * c
    return d


class Location:
    """Location class to convert lat/lon pairs to
    flat earth projection centered around capitol
    """
    capital_lat = 43.074683
    capital_lon = -89.384261

    def __init__(self, latlon=None, xy=None):
        if xy is not None:
            self.x, self.y = xy
        else:
            # If no latitude/longitude pair is given, use the capitol's
            if latlon is None:
                latlon = (Location.capital_lat, Location.capital_lon)

            # Calculate the x and y distance from the capital
            self.x = haversine_miles(Location.capital_lat, Location.capital_lon,
                                     Location.capital_lat, latlon[1])
            self.y = haversine_miles(Location.capital_lat, Location.capital_lon,
                                     latlon[0], Location.capital_lon)

            # Flip the sign of the x/y coordinates based on location
            if latlon[1] < Location.capital_lon:
                self.x *= -1

            if latlon[0] < Location.capital_lat:
                self.y *= -1

    def dist(self, other):
        """Calculate straight line distance between self and other"""
        return sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def __repr__(self):
        return "Location(xy=(%0.2f, %0.2f))" % (self.x, self.y)

class BusDay:

    def __init__(self,date_time):
        self.service_ids = self.__get_ids(date_time,self. __parse_file('mmt_gtfs.zip','calendar.txt'))
        self.__dftrips = self.__parse_file('mmt_gtfs.zip','trips.txt')
        self.__dfstop_times = self.__parse_file('mmt_gtfs.zip','stop_times.txt')
        self.__dfstops = self.__parse_file('mmt_gtfs.zip','stops.txt')
        self.trip_ids = self.__get_trip_ids()
        self.__stops_BST = BST(self.get_stops()) #bst with all stops for today
    
    def __parse_file(self, zip_file, text_file):
        with ZipFile(zip_file) as zf:
            with zf.open(text_file) as f:
                return pd.read_csv(f)
            
    def __get_ids(self,date_time,df):
        wkdys = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
        d = date_time
        service_ids = []
        df.apply(lambda row: self.__check_date(d, row['start_date'], row['end_date'], row['service_id'],row[wkdys[d.weekday()]], service_ids),axis=1)
        return sorted(service_ids)
    
    def __check_date(self,to_check,start,end,service_id,weekday,service_ids):
        s = datetime.strptime(str(start), '%Y%m%d')
        e = datetime.strptime(str(end), '%Y%m%d')
        if (s <= to_check and to_check <= e):
            if (weekday == 1):
                service_ids.append(service_id)
                
    def __get_trip_ids(self):
        df = self.__dftrips
        service_ids = self.service_ids
        trip_ids = []            
        rows = df[df["service_id"].isin(service_ids)]
        rows.apply(lambda x: trip_ids.append(x['trip_id']),axis=1)
        return trip_ids
        
    def get_trips(self,route=None):
        df = self.__dftrips
        service_ids = self.service_ids
        trips = []            
        rows = df[df["service_id"].isin(service_ids)]
        if route == None:
            rows.apply(lambda x: trips.append(Trip(x['trip_id'],x['route_short_name'],x['bikes_allowed'])),axis=1) 
        else:
            route_filter = rows[rows["route_short_name"] == route]
            route_filter.apply(lambda x: trips.append(Trip(x['trip_id'],x['route_short_name'],x['bikes_allowed'])),axis=1)
            
        return sorted(list(set(trips)))
    
    def get_stops(self):
        stop_ids = []
        stops = []
        df = self.__dfstop_times
        rows= df[df["trip_id"].isin(self.trip_ids)]
        rows.apply(lambda x: stop_ids.append(x['stop_id']), axis =1)
        df = self.__dfstops
        rows= df[df["stop_id"].isin(stop_ids)]
        rows.apply(lambda x: stops.append(Stop(x['stop_id'],Location(latlon = (x['stop_lat'],x['stop_lon'])),x['wheelchair_boarding'])),axis=1)
        
        return sorted(stops)
    
    
    def get_stops_rect(self, xx, yy):
        stops = self.__stops_BST.get_stops_rect(xx, yy)
        return stops
    
    
    def get_stops_circ(self, xy, radius):
        center = Location(xy = xy)
        x,y = xy
        #list of stops in the rectangle which the circle is inscribed in
        stops = self.get_stops_rect((x - radius, x + radius),(y - radius, y + radius))
        
        stops_in_radius = []
        #filters out stops outside radius
        for stop in stops:
            if stop.location.dist(center) < radius:
                stops_in_radius.append(stop)
        return stops_in_radius
    
    
    def __gett(self):
        stop_ids = []
        stops = []
        df = self.__dfstop_times
        rows= df[df["trip_id"].isin(self.trip_ids)]
        rows.apply(lambda x: stop_ids.append(x['stop_id']), axis =1)
        df = self.__dfstops
        rows= df[df["stop_id"].isin(stop_ids)]
        return rows
    
    def scatter_stops(self,ax):
        rows = self.__gett()
        rows = rows[rows["wheelchair_boarding"] == 1]
        rows['loc'] = rows.apply(lambda x: Location(latlon = (x['stop_lat'],x['stop_lon'])), axis = 1)
        rows['x'] = rows.apply(lambda x: x['loc'].x, axis = 1)
        rows['y'] = rows.apply(lambda x: x['loc'].y, axis = 1)
        rows.plot.scatter(x='x',y='y', s = 1.2 ,ax=ax,color='red')
        rows = self.__gett()
        rows = rows[rows["wheelchair_boarding"] == 0]
        rows['loc'] = rows.apply(lambda x: Location(latlon = (x['stop_lat'],x['stop_lon'])), axis = 1)
        rows['x'] = rows.apply(lambda x: x['loc'].x, axis = 1)
        rows['y'] = rows.apply(lambda x: x['loc'].y, axis = 1)
        rows.plot.scatter(x='x',y='y', s = 1.2, ax=ax,color='0.7')
    
    def draw_tree(self, ax):
        # limits on the axis
        xmin, xmax = ax.get_xlim() #(-100,100)
        ymin, ymax = ax.get_ylim() #(-100,100) 
        return self.__stops_BST.draw_tree(ax, xmin, xmax, ymin, ymax)
    
        

class Trip:
    def __init__(self, trip_id, route_id, bikes_allowed):
        self.trip_id = trip_id
        self.route_id = route_id
        self.bikes_allowed = self.__bike_to_bool(bikes_allowed)

    def __repr__(self):
        s = "Trip({}, {}, {})"
        return s.format(repr(self.trip_id), repr(self.route_id), repr(self.bikes_allowed))
    def __lt__(self, other):
        return (self.trip_id < other.trip_id)
    
    def __bike_to_bool(self, bikes_allowed):
        if bikes_allowed == 1:
            return True
        else:
            return False

class Stop:
    
    def __init__(self, stop_id, location,wheelchair_boarding):
        self.stop_id = stop_id
        self.location = location
        self.wheelchair_boarding = self.__wc_to_bool(wheelchair_boarding)
    
    def __repr__(self):
        s = "Stop({}, {}, {})"
        return s.format(repr(self.stop_id), repr(self.location), repr(self.wheelchair_boarding))
    
    def __lt__(self, other):
        return (self.stop_id < other.stop_id)
    
    def __wc_to_bool(self, wheelchair_boarding):
        if wheelchair_boarding == 1:
            return True
        else:
            return False
        
class Node:
    END_LEVEL = 6 # max height of tree starting at 0
    
    def __init__(self, level, stop_list):
        self.left = None
        self.right = None
        self.level = level
        self.stop_list = None
        
        if level == Node.END_LEVEL: # stop splitting, add data
            self.stop_list = stop_list
            
        else: # recusive case. split list to children
            if self.level % 2 == 0: # sort by x
                stop_list.sort(key = lambda stop: stop.location.x)
            else: # sort by y
                stop_list.sort(key = lambda stop: stop.location.y)
                
            split_index = len(stop_list)//2
            
            self.key = stop_list[split_index] #the value list is split at
            
            self.left = Node(self.level+1, stop_list[:split_index])
            self.right = Node(self.level+1, stop_list[split_index:])

class BST:
    def __init__(self, stop_list):
        self.root = Node(0, stop_list) #root has level 0
    
    #recursive method to get the stops in a rectangle
    #param root- root of the subtree
    def get_stops_rect(self, xx, yy,):
           return self.__get_stops_rect_help(xx, yy, self.root)
    
    def __get_stops_rect_help(self, xx, yy, root, stops = None):
        if stops == None:
            stops = []
        x1, x2 = xx
        y1, y2 = yy
        
        if root.level == Node.END_LEVEL: #base case
            for stop in root.stop_list: #filter stops down
                x = stop.location.x
                y = stop.location.y
                if x >= x1 and x <= x2 and y >= y1 and y <= y2:
                    stops.append(stop)
            return stops
        
        else: #recursive case
            if root.level % 2 == 0: #check x bounds
                if x2 < root.key.location.x: #all values in left subtree
                    stops = self.__get_stops_rect_help(xx, yy, root.left, stops)
                elif x1 > root.key.location.x: #all values in right subtree
                    stops = self.__get_stops_rect_help(xx, yy, root.right, stops)
                else: #values in both
                    stops = self.__get_stops_rect_help(xx, yy, root.left, stops)
                    stops = self.__get_stops_rect_help(xx, yy, root.right, stops)
            else: #check y bounds
                if y2 < root.key.location.y: #all values in left subtree
                    stops = self.__get_stops_rect_help(xx, yy, root.left, stops)
                elif y1 > root.key.location.y: #all values in right subtree
                    stops = self.__get_stops_rect_help(xx, yy, root.right, stops)
                else: #values in both
                    stops = self.__get_stops_rect_help(xx, yy, root.left, stops)
                    stops = self.__get_stops_rect_help(xx, yy, root.right, stops)
        return stops
        

    # param previous: The previous Node. It's key's location becomes the next bound
    #draws the tree splits by pre-order traversal
    def draw_tree(self, ax, xmin, xmax, ymin, ymax, node = None):
        if node == None:
            node = self.root
        if node.level == Node.END_LEVEL: #base case: no split, do nothing
            return #should we return here? or pass
            
        # location of the split point    
        point = node.key.location
        
        weight = -(node.level)+6 #weight of the line, decreasing as level increases
        # plot current Node's line
        if node.level % 2 == 0: # draw vertical line
            ax.plot((point.x, point.x),(ymin, ymax), lw = weight, color = "turquoise",zorder = -1)
            #draw the subtrees
            self.draw_tree(ax, xmin, point.x, ymin, ymax, node.left) #decrease x max bound going left
            self.draw_tree(ax, point.x, xmax, ymin, ymax, node.right) #increase x min bound going right

        else: # draw horizontal line
            ax.plot((xmin, xmax),(point.y, point.y), lw = weight, color = "turquoise", zorder= -1)
            #draw the subtrees
            self.draw_tree(ax, xmin, xmax, ymin, point.y, node.left) #decrease y max bound going left
            self.draw_tree(ax, xmin, xmax, point.y, ymax, node.right)#increase y min bound going right
    
    
    def get_keys(self):
        return self.__pre_order_traversal_help(self.root)
    #unused
    #param key_dict = dictionary of keys by axis they split on
    def __pre_order_traversal_help(self, node, key_dict = {'x':[], 'y':[]}):
        
        if node.level == Node.END_LEVEL: #base case
            return key_dict
        else:
            if node.level % 2 == 0:
                key_dict['y'].append(node.key)
            else:
                key_dict['x'].append(node.key)
            key_dict = self.__pre_order_traversal_help(node.left, key_dict)
            key_dict = self.__pre_order_traversal_help(node.right, key_dict)
            
        return key_dict