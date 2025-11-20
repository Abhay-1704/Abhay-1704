import xml.etree.ElementTree as ET
import math
import random

def parse_svg(svg_file):
    tree = ET.parse(svg_file)
    root = tree.getroot()
    
    # Namespace handling
    ns = {
        'ns0': 'http://www.w3.org/2000/svg',
        'xlink': 'http://www.w3.org/1999/xlink'
    }
    
    # Find and remove any existing animations and elements
    for elem in root.findall('.//ns0:animate', ns) + root.findall('.//ns0:animateMotion', ns) + root.findall('.//ns0:circle[@id="ball"]', ns) + root.findall('.//ns0:rect[@id="paddle"]', ns) or []:
        if elem in root:
            root.remove(elem)
    
    # Define your specific GitHub contribution colors
    TARGET_COLORS = {
        "#56d364",  # 15+
        "#2ea043",  # 10-14
        "#196c2e",  # 5-9
        "#033a16",  # 1-4
        "#151B23"   # 0 (background)
    }
    
    # Find all blocks matching your color scheme
    green_blocks = []
    green_shades = set()
    
    for rect in root.findall('.//ns0:rect', ns):
        fill = rect.get('fill', '').lower()
        if fill in TARGET_COLORS and fill != "#151B23":  # Exclude background color
            x = float(rect.get('x'))
            y = float(rect.get('y'))
            width = float(rect.get('width'))
            height = float(rect.get('height'))
            
            center_x = x + width / 2
            center_y = y + height / 2
            
            green_shades.add(fill)
            
            green_blocks.append({
                'x': x,
                'y': y,
                'width': width,
                'height': height,
                'center_x': center_x,
                'center_y': center_y,
                'color': fill,
                'used': False,
                'element': rect,
                'id': rect.get('id', f'block_{len(green_blocks)}')
            })
    
    return green_blocks, root, ns, sorted(green_shades, key=lambda x: int(x[1:], 16)), tree

def calculate_path_length(start_x, start_y, end_x, end_y):
    return math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)

def create_random_bottom_point(svg_width, svg_height):
    padding = 20
    return random.uniform(padding, svg_width - padding), svg_height - 10

def create_single_looping_animation(root, ns, all_paths, green_blocks, paddle_parts, color_to_part_index, initial_paddle_part_width, paddle_growth, svg_width, svg_height):
    # Create one big path that includes all movements
    all_path_data = []
    all_timings = []
    current_time = 0
    
    # Collect all path segments and timings
    for i, path_info in enumerate(all_paths):
        all_path_data.append(path_info['path_data'])
        all_timings.append({
            'start_time': current_time,
            'hit_time': current_time + path_info['to_block_duration'],
            'end_time': current_time + path_info['total_duration'],
            'block_element': path_info['block_element'],
            'block_color': path_info['block_color']
        })
        current_time += path_info['total_duration']
    
    total_duration = current_time
    
    # Create a single path for the entire sequence
    combined_path_data = " ".join(all_path_data).replace("M ", "L ").replace("L L", "L")
    combined_path_data = "M " + combined_path_data[2:]  # Fix the first M
    
    combined_path = ET.SubElement(root, '{%s}path' % ns['ns0'], {
        'd': combined_path_data,
        'fill': 'none',
        'stroke': 'none',
        'id': 'combinedPath'
    })
    
    # Create ball animation that loops
    animate_motion = ET.SubElement(root, '{%s}animateMotion' % ns['ns0'], {
        '{%s}href' % ns['xlink']: '#ball',
        'dur': f'{total_duration}s',
        'repeatCount': 'indefinite',
        'id': 'ballAnimation'
    })
    
    mpath = ET.SubElement(animate_motion, '{%s}mpath' % ns['ns0'], {
        '{%s}href' % ns['xlink']: f'#combinedPath'
    })
    
    # Create block animations that loop
    for i, timing in enumerate(all_timings):
        # Block disappears when hit
        animate_opacity_out = ET.SubElement(timing['block_element'], '{%s}animate' % ns['ns0'], {
            'attributeName': 'opacity',
            'values': '1;1;0;0',
            'keyTimes': f'0;{timing["hit_time"]/total_duration};{(timing["hit_time"]+0.01)/total_duration};1',
            'dur': f'{total_duration}s',
            'repeatCount': 'indefinite',
            'id': f'blockFade{i}'
        })
    
    # Create paddle animations that loop
    initial_total_width = initial_paddle_part_width * len(paddle_parts)
    initial_paddle_x = svg_width/2 - initial_total_width/2
    
    for part_index, part in enumerate(paddle_parts):
        # Calculate when this part gets hit and grows
        growth_times = []
        position_values = [str(initial_paddle_x + (part_index * initial_paddle_part_width))]
        width_values = [str(initial_paddle_part_width)]
        key_times = ['0']
        
        current_hits = 0
        current_x = initial_paddle_x + (part_index * initial_paddle_part_width)
        current_width = initial_paddle_part_width
        
        for i, timing in enumerate(all_timings):
            if color_to_part_index[timing['block_color']] == part_index:
                # This part grows
                current_hits += 1
                current_width = initial_paddle_part_width + (paddle_growth * current_hits)
            
            # Calculate new positions for all parts after this hit
            total_width = 0
            for j in range(len(paddle_parts)):
                hits_for_part = sum(1 for t in all_timings[:i+1] 
                                  if color_to_part_index[t['block_color']] == j)
                part_width = initial_paddle_part_width + (paddle_growth * hits_for_part)
                total_width += part_width
            
            # Center the paddle
            new_paddle_start = all_paths[i]['end_x'] - total_width/2
            new_x = new_paddle_start
            for j in range(part_index):
                hits_for_prev_part = sum(1 for t in all_timings[:i+1] 
                                       if color_to_part_index[t['block_color']] == j)
                prev_part_width = initial_paddle_part_width + (paddle_growth * hits_for_prev_part)
                new_x += prev_part_width
            
            position_values.append(str(new_x))
            width_values.append(str(current_width))
            key_times.append(str(timing['end_time']/total_duration))
        
        # Animate position
        if len(position_values) > 1:
            animate_x = ET.SubElement(part, '{%s}animate' % ns['ns0'], {
                'attributeName': 'x',
                'values': ';'.join(position_values),
                'keyTimes': ';'.join(key_times),
                'dur': f'{total_duration}s',
                'repeatCount': 'indefinite',
                'id': f'paddleX{part_index}'
            })
        
        # Animate width
        if len(width_values) > 1:
            animate_width = ET.SubElement(part, '{%s}animate' % ns['ns0'], {
                'attributeName': 'width',
                'values': ';'.join(width_values),
                'keyTimes': ';'.join(key_times),
                'dur': f'{total_duration}s',
                'repeatCount': 'indefinite',
                'id': f'paddleWidth{part_index}'
            })

def main(svg_file, output_file):
    green_blocks, root, ns, green_shades, tree = parse_svg(svg_file)
    
    if 'xmlns:xlink' not in root.attrib:
        root.attrib['xmlns:xlink'] = ns['xlink']
    
    if not green_blocks:
        print("No green blocks found in the SVG.")
        return
    
    svg_width = float(root.get('width'))
    svg_height = float(root.get('height'))
    
    # Create ball
    ball = ET.SubElement(root, '{%s}circle' % ns['ns0'], {
        'r': '6',
        'fill': 'red',
        'id': 'ball'
    })
    
    # Create paddle parts based on number of green shades
    color_to_part_index = {color: i for i, color in enumerate(green_shades)}
    
    # Paddle configuration
    initial_paddle_part_width = 10  # Base width for each part
    paddle_growth = 2  # How much each part grows per hit
    paddle_height = 10
    paddle_y = svg_height - 5  # Just above bottom
    
    paddle_parts = []
    initial_total_width = initial_paddle_part_width * len(green_shades)
    initial_paddle_x = svg_width/2 - initial_total_width/2  # Start centered
    
    for i, color in enumerate(green_shades):
        part = ET.SubElement(root, '{%s}rect' % ns['ns0'], {
            'width': str(initial_paddle_part_width),
            'height': str(paddle_height),
            'x': str(initial_paddle_x + (i * initial_paddle_part_width)),
            'y': str(paddle_y),
            'fill': color,
            'id': f'paddle_part_{i}',
            'hits': '0'
        })
        paddle_parts.append(part)
    
    # Start from center bottom
    start_x, start_y = svg_width/2, svg_height - 10
    current_x, current_y = start_x, start_y
    
    paths = []
    
    # Create a copy of green_blocks for pathfinding
    blocks_copy = [block.copy() for block in green_blocks]
    
    while any(not block['used'] for block in blocks_copy):
        # Find nearest unused block
        nearest_block = None
        min_distance = float('inf')
        
        for block in blocks_copy:
            if not block['used']:
                distance = math.sqrt((block['center_x'] - current_x)**2 + (block['center_y'] - current_y)**2)
                if distance < min_distance:
                    min_distance = distance
                    nearest_block = block
        
        if nearest_block:
            # Find the corresponding original block element
            original_block = None
            for orig_block in green_blocks:
                if (orig_block['center_x'] == nearest_block['center_x'] and 
                    orig_block['center_y'] == nearest_block['center_y']):
                    original_block = orig_block
                    break
            
            # Calculate path segments
            to_block_length = calculate_path_length(current_x, current_y, 
                                                 nearest_block['center_x'], 
                                                 nearest_block['center_y'])
            
            return_x, return_y = create_random_bottom_point(svg_width, svg_height)
            return_length = calculate_path_length(nearest_block['center_x'], nearest_block['center_y'],
                                              return_x, return_y)
            
            # Calculate durations (500px/second speed)
            to_block_duration = to_block_length / 500
            return_duration = return_length / 500
            total_duration = to_block_duration + return_duration
            
            # Create path data (ball goes to block, then back to paddle)
            path_data = f"M {current_x},{current_y} L {nearest_block['center_x']},{nearest_block['center_y']} L {return_x},{return_y}"
            
            paths.append({
                'path_data': path_data,
                'to_block_duration': to_block_duration,
                'total_duration': total_duration,
                'block_element': original_block['element'],
                'end_x': return_x,
                'end_y': return_y,
                'block_color': nearest_block['color']
            })
            
            nearest_block['used'] = True
            current_x, current_y = return_x, return_y
    
    # Create the single looping animation
    create_single_looping_animation(root, ns, paths, green_blocks, paddle_parts, 
                                   color_to_part_index, initial_paddle_part_width, 
                                   paddle_growth, svg_width, svg_height)
    
    # Save the modified SVG
    tree.write(output_file, encoding='utf-8', xml_declaration=True)
    print(f"Modified SVG saved to {output_file} with looping animation ({len(paths)} paths)")

if __name__ == "__main__":
    input_svg = "brickbreaker.svg"
    output_svg = "brickbreaker_with_paddle_looping.svg"
    main(input_svg, output_svg)
