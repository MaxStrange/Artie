union() {
// The Box
width = 5;
depth = 5;
height = 15;
translate([-width / 2, -depth / 2, 0]) cube([width, depth, height]);

// Cylinders
cyl_height = width * 2;
cyl_radius = depth / 2;
xrot = 90;
zrot = 90;
// Cylinder 0
cyl0x = -cyl_height/2;
cyl0y = 0;
cyl0z = height - cyl_radius;
// Cylinder 1
cyl1x = -cyl_height/2;
cyl1y = 0;
cyl1z = cyl_radius;

translate([cyl0x, cyl0y, cyl0z]) rotate(a=[xrot, 0, zrot]) cylinder(cyl_height, cyl_radius, cyl_radius);

translate([cyl1x, cyl1y, cyl1z]) rotate(a=[xrot, 0, zrot]) cylinder(cyl_height, cyl_radius, cyl_radius);
}