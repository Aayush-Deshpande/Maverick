( function () {

	class DRACOLoader extends THREE.Loader {

		constructor( manager ) {

			super( manager );

			this.decoderPath = '';
			this.decoderConfig = {};
			this.decoderBinary = null;
			this.decoderPending = null;

			this.workerLimit = 4;
			this.workerPool = [];
			this.workerNextTaskID = 1;
			this.workerSourceURL = '';

			this.defaultAttributeIDs = {
				position: 'POSITION',
				normal: 'NORMAL',
				color: 'COLOR',
				uv: 'TEX_COORD'
			};
			this.defaultAttributeTypes = {
				position: 'Float32Array',
				normal: 'Float32Array',
				color: 'Float32Array',
				uv: 'Float32Array'
			};

		}

		setDecoderPath( path ) {

			this.decoderPath = path;
			return this;

		}

		setDecoderConfig( config ) {

			this.decoderConfig = config;
			return this;

		}

		setWorkerLimit( limit ) {

			this.workerLimit = limit;
			return this;

		}

		load( url, onLoad, onProgress, onError ) {

			const loader = new THREE.FileLoader( this.manager );

			loader.setPath( this.path );
			loader.setResponseType( 'arraybuffer' );
			loader.setRequestHeader( this.requestHeader );
			loader.setWithCredentials( this.withCredentials );

			loader.load( url, ( buffer ) => {

				this.decodeDracoFile( buffer, onLoad, null, null, onError );

			}, onProgress, onError );

		}

		decodeDracoFile( buffer, callback, attributeUniqueIdMap, attributeTypeMap, onError ) {

			const taskConfig = {
				attributeUniqueIdMap: attributeUniqueIdMap || this.defaultAttributeIDs,
				attributeTypeMap: attributeTypeMap || this.defaultAttributeTypes,
				useUniqueIDs: !! attributeUniqueIdMap
			};

			this.decodeGeometry( buffer, taskConfig )
				.then( callback )
				.catch( onError );

		}

		decodeGeometry( buffer, taskConfig ) {

			// Clean clone & sanitize taskConfig so all values are JSON-serializable primitives for Web Worker postMessage
			const cleanTaskConfig = {
				useUniqueIDs: Boolean( taskConfig && taskConfig.useUniqueIDs ),
				attributeUniqueIdMap: {},
				attributeTypeMap: {}
			};

			if ( taskConfig && taskConfig.attributeUniqueIdMap ) {
				for ( const key in taskConfig.attributeUniqueIdMap ) {
					cleanTaskConfig.attributeUniqueIdMap[ key ] = taskConfig.attributeUniqueIdMap[ key ];
				}
			}

			if ( taskConfig && taskConfig.attributeTypeMap ) {
				for ( const key in taskConfig.attributeTypeMap ) {
					const val = taskConfig.attributeTypeMap[ key ];
					cleanTaskConfig.attributeTypeMap[ key ] = ( typeof val === 'function' ? val.name : String( val ) );
				}
			}

			taskConfig = cleanTaskConfig;
			const taskKey = JSON.stringify( taskConfig );

			// Check for an existing task.
			if ( THREE.DRACOLoader._taskCache.has( buffer ) ) {

				const taskDatabase = THREE.DRACOLoader._taskCache.get( buffer );

				if ( taskDatabase.has( taskKey ) ) {

					return taskDatabase.get( taskKey ).promise;

				}

			}

			let worker;
			const taskID = this.workerNextTaskID ++;
			const taskCost = buffer.byteLength;

			// Obtain a worker and assign a task, and get a promise.
			const geometryPending = this._getWorker( taskID, taskCost )
				.then( ( _worker ) => {

					worker = _worker;

					return new Promise( ( resolve, reject ) => {

						worker._callbacks[ taskID ] = { resolve, reject };

						const transferables = [];
						if ( buffer instanceof ArrayBuffer ) {
							transferables.push( buffer );
						} else if ( buffer && buffer.buffer instanceof ArrayBuffer && buffer.byteOffset === 0 && buffer.byteLength === buffer.buffer.byteLength ) {
							transferables.push( buffer.buffer );
						}

						worker.postMessage( { type: 'decode', id: taskID, taskConfig, buffer }, transferables );

					} );

				} )
				.then( ( message ) => this._createGeometry( message.geometry ) );

			// Cache the task result.
			if ( ! THREE.DRACOLoader._taskCache.has( buffer ) ) {

				THREE.DRACOLoader._taskCache.set( buffer, new Map() );

			}

			THREE.DRACOLoader._taskCache.get( buffer ).set( taskKey, { promise: geometryPending } );

			return geometryPending.finally( () => {

				if ( worker ) this._releaseWorker( worker );

			} );

		}

		_createGeometry( geometryData ) {

			const geometry = new THREE.BufferGeometry();

			if ( geometryData.index ) {

				geometry.setIndex( new THREE.BufferAttribute( geometryData.index.array, 1 ) );

			}

			for ( let i = 0; i < geometryData.attributes.length; i ++ ) {

				const attribute = geometryData.attributes[ i ];
				const name = attribute.name;
				const array = attribute.array;
				const itemSize = attribute.itemSize;

				geometry.setAttribute( name, new THREE.BufferAttribute( array, itemSize ) );

			}

			return geometry;

		}

		_loadLibrary( url, responseType ) {

			const loader = new THREE.FileLoader( this.manager );
			loader.setPath( this.decoderPath );
			loader.setResponseType( responseType );
			loader.setRequestHeader( this.requestHeader );
			loader.setWithCredentials( this.withCredentials );

			return new Promise( ( resolve, reject ) => {

				loader.load( url, resolve, undefined, reject );

			} );

		}

		preload() {

			this._initDecoder();
			return this;

		}

		_initDecoder() {

			if ( this.decoderPending ) return this.decoderPending;

			const useJS = typeof WebAssembly !== 'object' || this.decoderConfig.type === 'js';
			const librariesPending = [];

			if ( useJS ) {

				librariesPending.push( this._loadLibrary( 'draco_decoder.js', 'text' ) );

			} else {

				librariesPending.push( this._loadLibrary( 'draco_wasm_wrapper.js', 'text' ) );
				librariesPending.push( this._loadLibrary( 'draco_decoder.wasm', 'arraybuffer' ) );

			}

			this.decoderPending = Promise.all( librariesPending )
				.then( ( libraries ) => {

					const jsContent = libraries[ 0 ];

					if ( ! useJS ) {

						this.decoderConfig.wasmBinary = libraries[ 1 ];

					}

					const fn = THREE.DRACOLoader.DRACOWorker.toString();

					const body = [
						'/* draco decoder */',
						jsContent,
						'',
						'/* worker */',
						fn,
						'DRACOWorker();'
					].join( '\n' );

					this.workerSourceURL = URL.createObjectURL( new Blob( [ body ] ) );

				} );

			return this.decoderPending;

		}

		_getWorker( taskID, taskCost ) {

			return this._initDecoder().then( () => {

				if ( this.workerPool.length < this.workerLimit ) {

					const worker = new Worker( this.workerSourceURL );

					worker._callbacks = {};
					worker._taskCost = 0;

					const configCopy = Object.assign( {}, this.decoderConfig );
					if ( configCopy.wasmBinary && configCopy.wasmBinary instanceof ArrayBuffer ) {
						configCopy.wasmBinary = configCopy.wasmBinary.slice( 0 );
					}

					worker.postMessage( { type: 'init', decoderConfig: configCopy } );

					worker.onmessage = function ( e ) {

						const message = e.data;

						switch ( message.type ) {

							case 'decode':
								worker._callbacks[ message.id ].resolve( message );
								break;

							case 'error':
								worker._callbacks[ message.id ].reject( message );
								break;

							default:
								console.error( 'THREE.DRACOLoader: Unexpected message, "' + message.type + '"' );

						}

					};

					this.workerPool.push( worker );

				}

				// Sort workers by cost, ascend.
				this.workerPool.sort( function ( a, b ) {

					return a._taskCost - b._taskCost;

				} );

				const worker = this.workerPool[ 0 ];
				worker._taskCost += taskCost;

				return worker;

			} );

		}

		_releaseWorker( worker ) {

			worker._taskCost -= 1;

		}

		dispose() {

			for ( let i = 0; i < this.workerPool.length; i ++ ) {

				this.workerPool[ i ].terminate();

			}

			this.workerPool.length = 0;

			return this;

		}

	}

	DRACOLoader.DRACOWorker = function DRACOWorker() {

		let decoderConfig;
		let decoderPending;

		onmessage = function ( e ) {

			const message = e.data;

			switch ( message.type ) {

				case 'init':
					decoderConfig = message.decoderConfig;
					decoderPending = new Promise( function ( resolve/*, reject*/ ) {

						decoderConfig.onModuleLoaded = function ( draco ) {

							// Module is Promise-like.
							resolve( { draco: draco } );

						};

						DracoDecoderModule( decoderConfig ); // eslint-disable-line no-undef

					} );
					break;

				case 'decode':
					const buffer = message.buffer;
					const taskConfig = message.taskConfig;
					decoderPending.then( ( module ) => {

						const draco = module.draco;
						const decoder = new draco.Decoder();
						const decoderBuffer = new draco.DecoderBuffer();
						let rawBuffer;
						if ( buffer instanceof ArrayBuffer ) {
							rawBuffer = new Int8Array( buffer );
						} else if ( buffer && buffer.buffer instanceof ArrayBuffer ) {
							rawBuffer = new Int8Array( buffer.buffer, buffer.byteOffset || 0, buffer.byteLength );
						} else {
							rawBuffer = new Int8Array( buffer );
						}
						decoderBuffer.Init( rawBuffer, buffer.byteLength || rawBuffer.byteLength );

						try {

							const geometry = decodeGeometry( draco, decoder, decoderBuffer, taskConfig );

							const buffers = geometry.attributes.map( ( attr ) => attr.array.buffer );

							if ( geometry.index ) buffers.push( geometry.index.array.buffer );

							self.postMessage( { type: 'decode', id: message.id, geometry }, buffers );

						} catch ( error ) {

							console.error( error );

							self.postMessage( { type: 'error', id: message.id, error: error.message } );

						} finally {

							draco.destroy( decoderBuffer );
							draco.destroy( decoder );

						}

					} );
					break;

			}

		};

		function decodeGeometry( draco, decoder, decoderBuffer, taskConfig ) {

			let dracoGeometry;
			let decodingStatus;

			const geometryType = decoder.GetEncodedGeometryType( decoderBuffer );

			if ( geometryType === draco.TRIANGULAR_MESH ) {

				dracoGeometry = new draco.Mesh();
				decodingStatus = decoder.DecodeBufferToMesh( decoderBuffer, dracoGeometry );

			} else {

				throw new Error( 'THREE.DRACOLoader: Unexpected geometry type.' );

			}

			if ( ! decodingStatus.ok() || dracoGeometry.ptr === 0 ) {

				throw new Error( 'THREE.DRACOLoader: Decoding failed: ' + decodingStatus.error_msg() );

			}

			const geometry = { index: null, attributes: [] };

			// Gather attributes
			for ( const attributeName in taskConfig.attributeUniqueIdMap ) {

				const attributeType = self[ taskConfig.attributeTypeMap[ attributeName ] ];

				let attribute;
				let attributeID;

				if ( taskConfig.useUniqueIDs ) {

					attributeID = taskConfig.attributeUniqueIdMap[ attributeName ];
					attribute = decoder.GetAttributeByUniqueId( dracoGeometry, attributeID );

				} else {

					attributeID = decoder.GetAttributeId( dracoGeometry, draco[ taskConfig.attributeUniqueIdMap[ attributeName ] ] );

					if ( attributeID === - 1 ) continue;

					attribute = decoder.GetAttribute( dracoGeometry, attributeID );

				}

				geometry.attributes.push( decodeAttribute( draco, decoder, dracoGeometry, attributeName, attributeType, attribute ) );

			}

			// Add index of indices
			if ( geometryType === draco.TRIANGULAR_MESH ) {

				geometry.index = decodeIndex( draco, decoder, dracoGeometry );

			}

			draco.destroy( dracoGeometry );

			return geometry;

		}

		function decodeIndex( draco, decoder, dracoGeometry ) {

			const numFaces = dracoGeometry.num_faces();
			const numIndices = numFaces * 3;
			const byteLength = numIndices * 4;

			const ptr = draco._malloc( byteLength );
			decoder.GetTrianglesUInt32Array( dracoGeometry, byteLength, ptr );
			const index = new Uint32Array( draco.HEAPF32.buffer, ptr, numIndices ).slice();
			draco._free( ptr );

			return { array: index, itemSize: 1 };

		}

		function decodeAttribute( draco, decoder, dracoGeometry, attributeName, attributeType, attribute ) {

			const numComponents = attribute.num_components();
			const numPoints = dracoGeometry.num_points();
			const numValues = numPoints * numComponents;
			const byteLength = numValues * attributeType.BYTES_PER_ELEMENT;
			const dataType = getDracoDataType( draco, attributeType );

			const ptr = draco._malloc( byteLength );
			decoder.GetAttributeDataArrayForAllPoints( dracoGeometry, attribute, dataType, byteLength, ptr );
			const array = new attributeType( draco.HEAPF32.buffer, ptr, numValues ).slice();
			draco._free( ptr );

			return {
				name: attributeName,
				array: array,
				itemSize: numComponents
			};

		}

		function getDracoDataType( draco, attributeType ) {

			switch ( attributeType ) {

				case Float32Array: return draco.DT_FLOAT32;
				case Int8Array: return draco.DT_INT8;
				case Int16Array: return draco.DT_INT16;
				case Int32Array: return draco.DT_INT32;
				case Uint8Array: return draco.DT_UINT8;
				case Uint16Array: return draco.DT_UINT16;
				case Uint32Array: return draco.DT_UINT32;

			}

		}

	};

	THREE.DRACOLoader = DRACOLoader;
	THREE.DRACOLoader._taskCache = new Map();

} )();
