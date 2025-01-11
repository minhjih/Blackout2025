import json
import folium
import pandas as pd
from shapely.geometry import Polygon, Point
from shapely.ops import nearest_points
import geopandas as gpd
from folium.plugins import HeatMap
from sklearn.cluster import KMeans
import numpy as np
import os
import base64
from branca.element import IFrame

def load_geofence_data(json_path):
    """GeoJSON 데이터 로드"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def create_service_area_map(data):
    """서비스 영역 시각화"""
    # 서비스 영역의 경계 좌표 찾기
    all_coords = []
    for region in data.get('service_regions', []):
        for path in region.get('paths', []):
            all_coords.extend(path.get('outer_coords', []))
    
    # 경계 좌표로 최대/최소 위도/경도 계산 (좌표 순서 수정)
    lngs = [coord[0] for coord in all_coords]  # 경도
    lats = [coord[1] for coord in all_coords]  # 위도
    min_lat, max_lat = min(lats), max(lats)
    min_lng, max_lng = min(lngs), max(lngs)
    
    # 지도 중심점 계산 (위도, 경도 순서)
    center_lat = (min_lat + max_lat) / 2
    center_lng = (min_lng + max_lng) / 2
    
    # 기본 지도 생성
    m = folium.Map(location=[center_lat, center_lng], 
                  zoom_start=14,
                  tiles='CartoDB positron',
                  min_zoom=12,  # 최소 줌 레벨 설정
                  max_zoom=18,  # 최대 줌 레벨 설정
                  max_bounds=True,  # 경계 제한 활성화
                  min_lat=min_lat,
                  max_lat=max_lat,
                  min_lon=min_lng,
                  max_lon=max_lng)
    
    # 경계 설정
    m.fit_bounds([[min_lat, min_lng], [max_lat, max_lng]])
    
    # 경계를 벗어나지 못하도록 제한
    m.options['maxBounds'] = [[min_lat, min_lng], [max_lat, max_lng]]
    
    # 폴리곤 생성 시 좌표 순서 변환
    for region in data.get('service_regions', []):
        for path in region.get('paths', []):
            # 외곽 경계선 - 좌표 순서 변환 ([lng, lat] -> [lat, lng])
            outer_coords = [[coord[1], coord[0]] for coord in path.get('outer_coords', [])]
            folium.Polygon(
                locations=outer_coords,
                color='blue',
                fill=True,
                popup='서비스 가능 영역',
                fill_color='blue',
                fill_opacity=0.2,
                weight=2,
                smoothFactor=1.5
            ).add_to(m)
            
            # 내부 제외 영역 - 좌표 순서 변환
            for inner in path.get('inner_coords', []):
                inner_coords = [[coord[1], coord[0]] for coord in inner]
                folium.Polygon(
                    locations=inner_coords,
                    color='red',
                    fill=True,
                    popup='서비스 제외 구역',
                    fill_color='red',
                    fill_opacity=0.2,
                    weight=2,
                    smoothFactor=1.5
                ).add_to(m)
    
    # 주차 금지 구역 표시
    for zone in data.get('no_parking_zones', []):
        folium.Polygon(
            locations=zone.get('bounds', []),
            color='black',
            fill=True,
            popup='주차 금지 구역',
            fill_color='black',
            fill_opacity=0.3
        ).add_to(m)
    
    # CSV 파일에서 기기 데이터 로드
    df = pd.read_csv('input/regionid_560_test_data.csv')
    
    # 기기 타입별로 다른 색상 사용
    device_colors = {
        'bicycle': 'blue',
        'kickboard': 'green'
    }
    
    # 각 기기를 지도에 마커로 표시
    for _, row in df.iterrows():
        folium.CircleMarker(
            location=[row['end_lat'], row['end_lng']],
            radius=3,
            color=device_colors[row['MODEL_TYPE']],
            fill=True,
            popup=f"ID: {row['bicycle_id']}<br>Type: {row['MODEL_TYPE']}",
            weight=1
        ).add_to(m)
    
    # base station 찾기
    base_stations = find_base_stations('input/regionid_560_test_data.csv', data)
    
    # 각 base station의 인구밀도 계산
    df = pd.read_csv('input/regionid_560_test_data.csv')
    station_density = []
    for station in base_stations:
        radius = 0.0005  # 약 50m
        
        # 반경 내의 모든 포인트 찾기
        nearby_points = df[
            (df['end_lat'] - station[0])**2 + 
            (df['end_lng'] - station[1])**2 <= radius**2
        ]
        
        if len(nearby_points) == 0:
            station_density.append(0)
            continue
            
        # 각 포인트까지의 거리 계산
        distances = np.sqrt(
            (nearby_points['end_lat'] - station[0])**2 + 
            (nearby_points['end_lng'] - station[1])**2
        )
        
        # 거리에 따른 가중치 계산 (거리가 가까울수록 가중치 증가)
        # 지수 함수를 사용하여 거리에 따른 감쇠 효과 적용
        weights = np.exp(-10 * (distances / radius))  # -10은 감쇠 속도 조절 파라미터
        
        # 가중치가 적용된 밀집도 계산
        weighted_density = weights.sum()
        station_density.append(weighted_density)
    
    # 최대 인구밀도 찾기
    max_density = max(station_density) if station_density else 0
    
    # 이미지 파일 로드
    base_icon_path = os.path.join(os.getcwd(), 'input', 'base_station.png')
    gold_icon_path = os.path.join(os.getcwd(), 'input', 'gold_station.png')
    
    if not os.path.exists(base_icon_path) or not os.path.exists(gold_icon_path):
        print(f"Warning: Icon files not found")
        return
    
    # 이미지를 base64로 인코딩
    base_encoded = base64.b64encode(open(base_icon_path, 'rb').read())
    gold_encoded = base64.b64encode(open(gold_icon_path, 'rb').read())
    
    # base station 표시
    for i, (station, density) in enumerate(zip(base_stations, station_density)):
        # 인구밀도가 가장 높은 곳은 gold 이미지 사용
        encoded = gold_encoded if density == max_density else base_encoded
        
        # 이미지 HTML 생성
        html = f"""
            <div style="position: relative;">
                <img src="data:image/png;base64,{encoded.decode('UTF-8')}"
                     style="width:50px; height:80px; position: absolute; 
                            left: -25px; top: -40px;">
            </div>
        """
        
        # DivIcon 사용
        icon = folium.DivIcon(
            html=html,
            icon_size=(50, 80),
            icon_anchor=(25, 42)
        )
        
        # 팝업에 인구밀도 정보 추가
        popup_text = f'Base Station {i+1}<br>Density: {density} points'
        
        folium.Marker(
            location=[station[0], station[1]],
            popup=popup_text,
            icon=icon
        ).add_to(m)
    
    # output 폴더가 없으면 생성
    os.makedirs('output', exist_ok=True)
    
    # 결과 저장
    output_path = os.path.join('output', 'service_area_analysis.html')
    m.save(output_path)
    
    # HTML 파일 확인
    with open(output_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
        # base64 이미지가 포함되어 있는지 확인
        if 'data:image/png;base64,' in html_content:
            print("Base64 image found in HTML")
            # base64 이미지 문자열의 일부 출력 (처음 100자)
            start_idx = html_content.find('data:image/png;base64,')
            if start_idx != -1:
                print("Base64 image preview:", html_content[start_idx:start_idx+100])
        else:
            print("Warning: Base64 image not found in HTML")
    
    return m

def add_population_clusters(m, population_data_path):
    """시간대별 인구밀집도 클러스터링 및 시각화"""
    # 인구 데이터 로드 (CSV 파일 예시)
    df = pd.read_csv(population_data_path)
    
    # 시간대별 히트맵 데이터 생성
    heat_data = [[row['lat'], row['lng'], row['population']] 
                 for _, row in df.iterrows()]
    
    # 히트맵 추가
    HeatMap(heat_data).add_to(m)
    
    return m

def suggest_base_parking_areas(data, population_data, n_clusters=5):
    """인구밀집도 기반 base 주차구역 추천"""
    from sklearn.cluster import KMeans
    
    # 서비스 가능 영역 내의 인구밀집 포인트만 선택
    service_area_polygons = []
    for region in data['service_regions']:
        for path in region['paths']:
            outer = Polygon(path['outer_coords'])
            inners = [Polygon(inner) for inner in path.get('inner_coords', [])]
            # 내부 제외 영역을 고려한 서비스 영역
            for inner in inners:
                outer = outer.difference(inner)
            service_area_polygons.append(outer)
    
    # 주차 금지 구역 제외
    no_parking_polygons = [Polygon(zone['bounds']) 
                          for zone in data['no_parking_zones']]
    
    # 클러스터링 수행
    points = population_data[['lat', 'lng']].values
    kmeans = KMeans(n_clusters=n_clusters)
    clusters = kmeans.fit_predict(points)
    
    # 클러스터 중심점 반환
    return kmeans.cluster_centers_

def find_base_stations(data_path, geofence_data):
    """모든 차량의 base station을 찾는 함수"""
    # CSV 파일 읽기
    df = pd.read_csv(data_path)
    
    # 위도가 최소값인 데이터 제외
    min_lat = df['end_lat'].min()
    df_filtered = df[df['end_lat'] > min_lat]
    
    # 위치 데이터만 추출
    locations_df = df_filtered[['end_lat', 'end_lng']]
    
    # K-means 클러스터링 수행
    kmeans = KMeans(n_clusters=10, random_state=20, n_init='auto')
    clusters = kmeans.fit(locations_df)
    
    # base station 위치 (클러스터 중심점)
    base_stations = clusters.cluster_centers_
    
    # 서비스 가능 영역과 제외 구역 폴리곤 생성
    service_polygons = []
    excluded_polygons = []
    for region in geofence_data['service_regions']:
        for path in region['paths']:
            # 위도, 경도 순서로 변경 ([lng, lat] -> [lat, lng])
            outer = Polygon([[coord[1], coord[0]] for coord in path['outer_coords']])
            service_polygons.append(outer)
            
            for inner in path.get('inner_coords', []):
                # 위도, 경도 순서로 변경
                inner_poly = Polygon([[coord[1], coord[0]] for coord in inner])
                excluded_polygons.append(inner_poly)
    
    # 주차 금지 구역 폴리곤 생성 (위도, 경도 순서로 변경)
    no_parking_polygons = []
    for zone in geofence_data.get('no_parking_zones', []):
        coords = [[coord[1], coord[0]] for coord in zone['bounds']]
        no_parking_polygons.append(Polygon(coords))
    
    def is_valid_location(point):
        """위치가 유효한지 확인하는 함수"""
        return (any(polygon.contains(point) for polygon in service_polygons) and
                not any(polygon.contains(point) for polygon in excluded_polygons) and
                not any(polygon.contains(point) for polygon in no_parking_polygons)
                )
    
    def find_valid_location(station, initial_radius=0.0001, max_radius=0.005, radius_step=0.0001):
        """점진적으로 반경을 넓혀가며 유효한 위치 찾기"""
        current_radius = initial_radius
        while current_radius <= max_radius:
            # 현재 반경 내의 모든 데이터 포인트 확인
            nearby_points = locations_df[
                (locations_df['end_lat'] - station[0])**2 + 
                (locations_df['end_lng'] - station[1])**2 <= current_radius**2
            ]
            
            # 반경 내 포인트들 중 유효한 위치 찾기
            for _, row in nearby_points.iterrows():
                point = Point(row['end_lat'], row['end_lng'])
                if is_valid_location(point):
                    return [row['end_lat'], row['end_lng']]
            
            # 반경 증가
            current_radius += radius_step
        
        # 유효한 위치를 찾지 못한 경우 메시지 출력 후 원래 위치 반환
        #print(f"유효한 위치를 찾지 못했습니다. 원래 위치 ({station[0]}, {station[1]})를 사용합니다.")
        return [station[0], station[1]]
    
    # 각 base station 위치 조정
    valid_base_stations = []
    for station in base_stations:
        point = Point(station[0], station[1])
        if not is_valid_location(point):
            valid_location = find_valid_location(station)
            valid_base_stations.append(valid_location)
        else:
            valid_base_stations.append([station[0], station[1]])
    
    return np.array(valid_base_stations)

if __name__ == "__main__":
    # 데이터 로드
    geofence_data = load_geofence_data('input/강남대치_geo_fence.json')
    
    # 기본 지도 생성
    base_map = create_service_area_map(geofence_data)
    

    # 결과 저장
    #map_with_population.save('output/service_area_analysis.html') 
    base_map.save('output/service_area_analysis.html')